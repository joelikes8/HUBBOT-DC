"""
Community Engagement Cog for handling community interaction commands.
Includes commands for giveaways, daily tips, suggestions, voting, and leaderboards.
"""
import logging
import random
import asyncio
import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from database import Database
from config import BotConfig

logger = logging.getLogger(__name__)

class CommunityEngagement(commands.Cog):
    """Community engagement commands for server interaction"""
    
    def __init__(self, bot):
        self.bot = bot
        # Don't start tasks immediately to avoid issues with asyncio loops
        # They will be started via the before_loop event
    
    def cog_unload(self):
        """Clean up tasks when cog is unloaded"""
        self.check_giveaways.cancel()
        self.post_daily_tip.cancel()
    
    @app_commands.command(name="giveaway", description="Start a giveaway for Robux, free bots, or perks")
    @app_commands.describe(
        prize="What you're giving away",
        winners="Number of winners (default: 1)",
        duration="Duration in hours (default: 24)"
    )
    @app_commands.checks.has_any_role(BotConfig.ADMIN_ROLE_ID, BotConfig.STAFF_ROLE_ID)
    async def giveaway(self, interaction: discord.Interaction, prize: str, winners: int = 1, duration: int = 24):
        """Start a giveaway (Robux, free bots, perks)"""
        try:
            # Only staff can start giveaways
            if not any(role.id in (BotConfig.ADMIN_ROLE_ID, BotConfig.STAFF_ROLE_ID) 
                      for role in interaction.user.roles):
                await interaction.response.send_message(
                    "You don't have permission to start giveaways.",
                    ephemeral=True
                )
                return
            
            # Validate input
            if winners < 1:
                await interaction.response.send_message(
                    "The number of winners must be at least 1.",
                    ephemeral=True
                )
                return
            
            if duration < 1:
                await interaction.response.send_message(
                    "Giveaway duration must be at least 1 hour.",
                    ephemeral=True
                )
                return
            
            # Calculate end time
            end_time = datetime.datetime.now() + datetime.timedelta(hours=duration)
            
            # Create the giveaway embed
            embed = discord.Embed(
                title="🎉 GIVEAWAY 🎉",
                description=f"**Prize:** {prize}\n\n"
                           f"**Winners:** {winners}\n"
                           f"**Ends:** <t:{int(end_time.timestamp())}:R>\n\n"
                           "React with 🎉 to enter!",
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"Hosted by {interaction.user.name} • Ends at {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            # Defer the response while we set up the giveaway
            await interaction.response.defer(ephemeral=True)
            
            # Send the giveaway message
            channel = interaction.channel
            giveaway_message = await channel.send(embed=embed)
            
            # Add the reaction for entry
            await giveaway_message.add_reaction("🎉")
            
            # Store giveaway in the database
            await Database.create_giveaway(
                message_id=giveaway_message.id,
                channel_id=channel.id,
                creator_id=interaction.user.id,
                prize=prize,
                winner_count=winners,
                end_time=end_time
            )
            
            await interaction.followup.send(
                "Giveaway created successfully!",
                ephemeral=True
            )
        
        except Exception as e:
            logger.error(f"Error creating giveaway: {e}")
            await interaction.followup.send(
                "There was an error creating the giveaway. Please try again later.",
                ephemeral=True
            )
    
    @tasks.loop(minutes=5)
    async def check_giveaways(self):
        """Check for completed giveaways and pick winners"""
        try:
            # Get active giveaways that have ended
            active_giveaways = await Database.get_active_giveaways()
            now = datetime.datetime.now()
            
            for giveaway in active_giveaways:
                # Check if the giveaway has ended
                if giveaway['end_time'] <= now:
                    # Get the channel and message
                    channel = self.bot.get_channel(giveaway['channel_id'])
                    if not channel:
                        logger.error(f"Channel {giveaway['channel_id']} not found for giveaway {giveaway['id']}")
                        continue
                    
                    try:
                        message = await channel.fetch_message(giveaway['message_id'])
                    except discord.NotFound:
                        logger.error(f"Message {giveaway['message_id']} not found for giveaway {giveaway['id']}")
                        continue
                    
                    # Get the reactions
                    reaction = discord.utils.get(message.reactions, emoji="🎉")
                    if not reaction:
                        logger.error(f"No reactions found for giveaway {giveaway['id']}")
                        continue
                    
                    # Get the entries
                    users = []
                    async for user in reaction.users():
                        if not user.bot:  # Exclude bots
                            users.append(user)
                    
                    # Pick winners
                    winner_count = min(giveaway['winner_count'], len(users))
                    winners = []
                    
                    if users:
                        winners = random.sample(users, winner_count)
                        winner_mentions = [winner.mention for winner in winners]
                        winner_ids = [winner.id for winner in winners]
                        
                        # Update the giveaway embed
                        embed = message.embeds[0]
                        winners_text = ", ".join(winner_mentions) if winners else "No valid entries"
                        
                        new_embed = discord.Embed(
                            title="🎉 GIVEAWAY ENDED 🎉",
                            description=embed.description.split("\n\nReact with")[0] + f"\n\n**Winners:** {winners_text}",
                            color=discord.Color.dark_gold()
                        )
                        new_embed.set_footer(text=embed.footer.text)
                        
                        await message.edit(embed=new_embed)
                        
                        # Send winner announcement
                        if winners:
                            announcement = f"🎉 Congratulations {', '.join(winner_mentions)}! You won **{giveaway['prize']}**!"
                            await channel.send(announcement)
                    else:
                        # No valid entries
                        embed = message.embeds[0]
                        new_embed = discord.Embed(
                            title="🎉 GIVEAWAY ENDED 🎉",
                            description=embed.description.split("\n\nReact with")[0] + "\n\n**Winners:** No valid entries",
                            color=discord.Color.dark_gold()
                        )
                        new_embed.set_footer(text=embed.footer.text)
                        await message.edit(embed=new_embed)
                        await channel.send("No valid entries for the giveaway.")
                    
                    # Update giveaway in database
                    await Database.complete_giveaway(giveaway['id'], winner_ids if winners else None)
        
        except Exception as e:
            logger.error(f"Error checking giveaways: {e}", exc_info=True)
    
    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("Starting giveaway checking background task")
        # Start the task after the bot is ready
        if not self.check_giveaways.is_running():
            self.check_giveaways.start()
    
    @app_commands.command(name="daily-tip", description="Get a random bot idea or helpful tip")
    async def daily_tip(self, interaction: discord.Interaction):
        """Posts a random bot idea or helpful tip"""
        try:
            # Get a random tip from the database
            tip = await Database.get_random_tip()
            
            if not tip:
                # If no tips exist, provide a default one
                tip_text = "No custom tips available yet. Stay tuned for more helpful content!"
            else:
                tip_text = tip['tip_text']
            
            embed = discord.Embed(
                title="💡 Daily Bot Tip",
                description=tip_text,
                color=discord.Color.blue()
            )
            embed.set_footer(text="Use /suggest to submit your own tips!")
            
            await interaction.response.send_message(embed=embed)
            
            # Increment user's activity points
            await Database.increment_activity(interaction.user.id, 1)
        
        except Exception as e:
            logger.error(f"Error getting daily tip: {e}")
            await interaction.response.send_message(
                "There was an error getting a daily tip. Please try again later.",
                ephemeral=True
            )
    
    @tasks.loop(hours=24)
    async def post_daily_tip(self):
        """Automatically post a daily tip in the announcement channel"""
        if not BotConfig.ANNOUNCEMENT_CHANNEL_ID:
            return
        
        try:
            channel = self.bot.get_channel(BotConfig.ANNOUNCEMENT_CHANNEL_ID)
            if not channel:
                logger.error(f"Announcement channel {BotConfig.ANNOUNCEMENT_CHANNEL_ID} not found")
                return
            
            # Get a random tip
            tip = await Database.get_random_tip()
            
            if not tip:
                # Skip if no tips are available
                return
            
            embed = discord.Embed(
                title="💡 Daily Bot Tip",
                description=tip['tip_text'],
                color=discord.Color.blue()
            )
            embed.set_footer(text="Use /suggest to submit your own tips!")
            
            await channel.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error posting daily tip: {e}")
    
    @post_daily_tip.before_loop
    async def before_post_daily_tip(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("Starting daily tip background task")
        
        # Start the task after the bot is ready
        if not self.post_daily_tip.is_running():
            self.post_daily_tip.start()
            
        # Wait until a specific time (e.g., 9:00 AM)
        now = datetime.datetime.now()
        target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        
        if now >= target_time:
            # If we've already passed the target time today, wait until tomorrow
            target_time = target_time + datetime.timedelta(days=1)
        
        logger.info(f"Scheduled daily tip for {target_time}")
        await asyncio.sleep((target_time - now).total_seconds())
    
    @app_commands.command(name="suggest", description="Submit feedback or ideas for the server")
    @app_commands.describe(suggestion="Your feedback or idea")
    async def suggest(self, interaction: discord.Interaction, suggestion: str):
        """Submit feedback or ideas to improve the server"""
        try:
            # Store the feedback
            await Database.submit_feedback(interaction.user.id, "suggestion", suggestion)
            
            # Create a confirmation embed
            embed = discord.Embed(
                title="Suggestion Submitted",
                description="Thank you for your suggestion! Our team will review it.",
                color=discord.Color.green()
            )
            embed.add_field(name="Your Suggestion", value=suggestion, inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Increment user's activity points
            await Database.increment_activity(interaction.user.id, 2)
            
            # Notify staff if a channel is configured
            if BotConfig.ADMIN_ROLE_ID:
                # Find a staff member to notify
                for guild in self.bot.guilds:
                    for member in guild.members:
                        if any(role.id == BotConfig.ADMIN_ROLE_ID for role in member.roles):
                            try:
                                staff_embed = discord.Embed(
                                    title="New Suggestion",
                                    description=f"A new suggestion has been submitted by {interaction.user.mention}",
                                    color=discord.Color.blue()
                                )
                                staff_embed.add_field(name="Suggestion", value=suggestion, inline=False)
                                staff_embed.set_footer(text=f"User ID: {interaction.user.id}")
                                
                                await member.send(embed=staff_embed)
                                break
                            except discord.Forbidden:
                                # Cannot DM this user, try another
                                continue
        
        except Exception as e:
            logger.error(f"Error submitting suggestion: {e}")
            await interaction.response.send_message(
                "There was an error submitting your suggestion. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="vote", description="Get a link to vote for the server or bot")
    async def vote(self, interaction: discord.Interaction):
        """Link to vote for the server or bot on top.gg"""
        embed = discord.Embed(
            title="Vote for Our Bot",
            description="Support us by voting for our bot on these platforms:",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="Top.gg",
            value="[Vote on Top.gg](https://top.gg/bot/your-bot-id/vote)",
            inline=True
        )
        
        embed.add_field(
            name="Discord Bot List",
            value="[Vote on DBL](https://discordbotlist.com/bots/your-bot-id/upvote)",
            inline=True
        )
        
        embed.set_footer(text="Thank you for your support! Votes reset every 12 hours.")
        
        await interaction.response.send_message(embed=embed)
        
        # Increment user's activity points
        await Database.increment_activity(interaction.user.id, 1)
    
    @app_commands.command(name="leaderboard", description="See the top buyers or most active users")
    async def leaderboard(self, interaction: discord.Interaction):
        """See the top buyers or most active users"""
        try:
            # Get top users from the database
            top_users = await Database.get_leaderboard(10)
            
            if not top_users:
                await interaction.response.send_message(
                    "No user activity data available yet.",
                    ephemeral=True
                )
                return
            
            # Create the leaderboard embed
            embed = discord.Embed(
                title="🏆 Community Leaderboard",
                description="Our most active community members:",
                color=discord.Color.gold()
            )
            
            # Add each user to the leaderboard
            for i, user in enumerate(top_users, 1):
                user_obj = self.bot.get_user(user['discord_id'])
                username = user_obj.name if user_obj else f"User {user['discord_id']}"
                
                embed.add_field(
                    name=f"{i}. {username}",
                    value=f"Activity Points: **{user['activity_points']}**\nOrders: **{user['orders_count']}**",
                    inline=(i % 2 == 0)  # Alternate inline
                )
            
            embed.set_footer(text="Activity points are earned by using bot commands and participating in the community.")
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            await interaction.response.send_message(
                "There was an error loading the leaderboard. Please try again later.",
                ephemeral=True
            )

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(CommunityEngagement(bot))
