"""
Bot configuration and setup.
This file contains the bot configuration and startup logic.
"""
import os
import logging
import asyncio
import discord
from discord.ext import commands
from config import BotConfig

logger = logging.getLogger(__name__)

def setup_bot():
    """Setup and configure the bot with all required extensions"""
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.DEBUG)
    
    logger.info("Setting up Discord bot...")
    
    # Set intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    logger.info(f"Intents configured: message_content={intents.message_content}, members={intents.members}")
    
    # Initialize bot with command prefix and intents
    bot = commands.Bot(
        command_prefix=BotConfig.COMMAND_PREFIX, 
        intents=intents,
        # Auto-sync slash commands with Discord
        sync_commands=True,
        # Register commands globally for faster updates
        sync_commands_debug=True
    )
    
    @bot.event
    async def on_ready():
        """Called when the bot is ready and connected to Discord"""
        logger.info(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
        logger.info(f"Connected to {len(bot.guilds)} guilds")
        
        try:
            # Try to manually sync slash commands
            synced = await bot.tree.sync()
            logger.info(f"Successfully synced {len(synced)} application commands with Discord")
            
            # Log the available commands
            if synced:
                for cmd in synced:
                    logger.info(f"  - /{cmd.name}: {cmd.description if hasattr(cmd, 'description') else 'No description'}")
            else:
                logger.warning("No application commands were synced")
                
        except Exception as e:
            logger.error(f"Error syncing commands: {e}", exc_info=True)
        
        # Set bot activity status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for /help | Custom Bot Orders"
        )
        await bot.change_presence(activity=activity)
        
        logger.info("Bot is ready!")
    
    @bot.event
    async def on_command_error(ctx, error):
        """Global error handler for bot commands"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}. Use `/help {ctx.command.name}` for proper usage.")
            return
            
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument provided. Use `/help {ctx.command.name}` for proper usage.")
            return
            
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
            return
            
        logger.error(f"Command error: {error}", exc_info=error)
        await ctx.send("An error occurred while processing your command. Please try again later.")
    
    # Load extensions (cogs)
    async def load_extensions():
        """Load all cog extensions"""
        await bot.load_extension("cogs.order_management")
        await bot.load_extension("cogs.community_engagement")
        await bot.load_extension("cogs.support_tools")
        await bot.load_extension("cogs.admin")
        logger.info("All extensions loaded successfully")
    
    # Setup hook to load extensions
    @bot.event
    async def setup_hook():
        """Called when the bot is setting up"""
        await load_extensions()
        
        # Also try syncing commands during setup
        try:
            await bot.tree.sync()
            logger.info("Synced commands during setup phase")
        except Exception as e:
            logger.error(f"Failed to sync commands during setup: {e}")
    
    return bot
