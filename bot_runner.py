#!/usr/bin/env python3

import os
import asyncio
import logging
import sys

from bot import setup_bot
from database import Database
from config import BotConfig

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    # Check for token
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set or is empty")
        return 1
    
    logger.info(f"Using token (first 5 chars): {token[:5]}...")
    
    # Initialize database
    try:
        logger.info("Initializing database connection...")
        await Database.create_pool()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return 1
    
    # Setup bot
    try:
        logger.info("Setting up Discord bot...")
        bot = setup_bot()
        logger.info("Bot configured successfully")
        
        # Run the bot
        logger.info("Starting bot...")
        await bot.start(token)
    except Exception as e:
        logger.error(f"Error running Discord bot: {e}", exc_info=True)
        return 1
    finally:
        if Database._pool is not None:
            logger.info("Closing database connection...")
            await Database.close_pool()
    
    return 0

if __name__ == "__main__":
    logger.info("Starting Discord bot runner...")
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
