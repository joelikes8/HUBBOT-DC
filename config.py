"""
Configuration settings for the bot and web application.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BotConfig:
    """Configuration settings for the bot and web application"""
    # Bot configuration
    COMMAND_PREFIX = "!"
    
    # Database configuration
    DB_HOST = os.environ.get("PGHOST")
    DB_PORT = os.environ.get("PGPORT")
    DB_USER = os.environ.get("PGUSER")
    DB_PASSWORD = os.environ.get("PGPASSWORD")
    DB_NAME = os.environ.get("PGDATABASE")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    # Order status options
    ORDER_STATUSES = [
        "pending_payment",
        "payment_received",
        "in_progress",
        "testing",
        "completed",
        "cancelled"
    ]
    
    # Pricing information
    PRICING = {
        "basic": {"price": 100, "description": "Simple command-based bot with basic functionality"},
        "standard": {"price": 250, "description": "Bot with multiple commands, basic database functionality"},
        "premium": {"price": 500, "description": "Advanced bot with database, web dashboard, custom features"},
        "custom": {"price": "Custom", "description": "Fully customized solution based on specific requirements"}
    }
    
    # Admin and staff role IDs (to be set by server admin)
    ADMIN_ROLE_ID = int(os.environ.get("ADMIN_ROLE_ID", "0"))
    STAFF_ROLE_ID = int(os.environ.get("STAFF_ROLE_ID", "0"))
    
    # Channels
    ORDER_CHANNEL_ID = int(os.environ.get("ORDER_CHANNEL_ID", "0"))
    ANNOUNCEMENT_CHANNEL_ID = int(os.environ.get("ANNOUNCEMENT_CHANNEL_ID", "0"))
    
    # Cooldowns (in seconds)
    DAILY_TIP_COOLDOWN = 86400  # 24 hours
    VOTE_COOLDOWN = 43200  # 12 hours
    SUGGEST_COOLDOWN = 3600  # 1 hour
    
    # Web application settings
    SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-secret-key")
    FLASK_HOST = "0.0.0.0"
    FLASK_PORT = 5000
    DISCORD_INVITE_URL = "https://discord.gg/your-server"
    DISCORD_BOT_INVITE_URL = os.environ.get("DISCORD_BOT_INVITE_URL", "")
    SUPPORT_EMAIL = "support@example.com"
