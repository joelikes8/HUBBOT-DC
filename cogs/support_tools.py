"""
Support Tools Cog for handling bug reports, support requests, and FAQs.
"""
import logging
import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from config import BotConfig

logger = logging.getLogger(__name__)

class SupportTools(commands.Cog):
    """Support tools for helping users with issues"""
    
    def __init__(self, bot):
        self.bot = bot
        # Store frequently asked questions and answers
        self.faq_data = {
            "payment": {
                "question": "How do I make a payment?",
                "answer": "We accept Robux payments through gamepasses. Use `/link` to connect your Roblox account, then follow the specific payment instructions for your order."
            },
            "wait": {
                "question": "How long does it take to complete an order?",
                "answer": "Basic bots typically take 1-3 days, standard bots 3-7 days, and premium/custom bots 7-14 days depending on complexity."
            },
            "refund": {
                "question": "What is your refund policy?",
                "answer": "Refunds are available if work hasn't started on your order. Once development begins, partial refunds may be offered based on completion status."
            },
            "features": {
                "question": "Can I add more features after ordering?",
                "answer": "Yes! Additional features can be added during development for an adjusted price. Contact support for more details."
            },
            "hosting": {
                "question": "Do you provide bot hosting?",
                "answer": "We provide instructions for self-hosting your bot. For an additional fee, we can also arrange hosting solutions."
            },
            "support": {
                "question": "How long do I get support after my bot is delivered?",
                "answer": "All bots come with 30 days of free support for bug fixes. Extended support plans are available for purchase."
            },
            "source": {
                "question": "Do I get the source code of my bot?",
                "answer": "Yes, you'll receive the full source code of your custom bot upon completion and final payment."
            }
        }
    
    @app_commands.command(name="report", description="Report a bug or issue with a bot")
    @app_commands.describe(issue="Describe the bug or issue you're experiencing")
    async def report(self, interaction: discord.Interaction, issue: str):
        """Report a bug or problem with a bot"""
        try:
            # Store the bug report
            await Database.submit_feedback(interaction.user.id, "bug", issue)
            
            # Create a confirmation embed
            embed = discord.Embed(
                title="Bug Report Submitted",
                description="Thank you for your report! Our team will investigate this issue.",
                color=discord.Color.red()
            )
            embed.add_field(name="Your Report", value=issue, inline=False)
            embed.set_footer(text="A staff member will contact you if more information is needed.")
            
            await interaction.response.send_message(embed=embed)
            
            # Notify staff if a staff role is configured
            if BotConfig.STAFF_ROLE_ID:
                # Find a staff channel to notify
                for guild in self.bot.guilds:
                    for channel in guild.text_channels:
                        if "staff" in channel.name or "admin" in channel.name:
                            try:
                                staff_embed = discord.Embed(
                                    title="🐞 New Bug Report",
                                    description=f"A new bug report has been submitted by {interaction.user.mention}",
                                    color=discord.Color.dark_red()
                                )
                                staff_embed.add_field(name="Bug Report", value=issue, inline=False)
                                staff_embed.add_field(name="User ID", value=str(interaction.user.id), inline=True)
                                staff_embed.add_field(name="Username", value=interaction.user.name, inline=True)
                                
                                await channel.send(f"<@&{BotConfig.STAFF_ROLE_ID}>", embed=staff_embed)
                                break
                            except discord.Forbidden:
                                # Cannot send to this channel, try another
                                continue
        
        except Exception as e:
            logger.error(f"Error submitting bug report: {e}")
            await interaction.response.send_message(
                "There was an error submitting your bug report. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="support", description="Get information on how to contact staff for help")
    async def support(self, interaction: discord.Interaction):
        """Shows how to contact staff or get help"""
        embed = discord.Embed(
            title="Customer Support",
            description="Need help with your order or have questions? Here's how to reach us:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 Report a Bug",
            value="Use `/report` to submit any issues you're experiencing with your bot.",
            inline=False
        )
        
        embed.add_field(
            name="❓ Frequently Asked Questions",
            value="Check `/faq` for answers to common questions.",
            inline=False
        )
        
        embed.add_field(
            name="📞 Direct Support",
            value="For urgent matters, tag @Staff in the #support channel.\nEmail: support@example.com",
            inline=False
        )
        
        embed.add_field(
            name="⏰ Support Hours",
            value="Our team is available Monday-Friday, 9 AM - 5 PM EST.\nResponse time: Usually within 24 hours.",
            inline=False
        )
        
        embed.set_footer(text="We're here to help! Thank you for your patience.")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="faq", description="View answers to common questions")
    @app_commands.describe(topic="Specific FAQ topic (optional)")
    async def faq(self, interaction: discord.Interaction, topic: str = None):
        """View answers to common questions and concerns"""
        # If a specific topic was requested
        if topic and topic.lower() in self.faq_data:
            faq_item = self.faq_data[topic.lower()]
            embed = discord.Embed(
                title=faq_item["question"],
                description=faq_item["answer"],
                color=discord.Color.blue()
            )
            embed.set_footer(text="Use /faq without a topic to see all available questions.")
            
            await interaction.response.send_message(embed=embed)
            return
        
        # If no topic or invalid topic, show the full FAQ
        embed = discord.Embed(
            title="Frequently Asked Questions",
            description="Here are answers to our most common questions. Use `/faq [topic]` for specific details.",
            color=discord.Color.blue()
        )
        
        for key, faq_item in self.faq_data.items():
            embed.add_field(
                name=faq_item["question"],
                value=f"Use `/faq {key}` for details",
                inline=False
            )
        
        embed.set_footer(text="If your question isn't answered here, use /support for more help.")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(SupportTools(bot))
