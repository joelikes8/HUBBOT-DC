"""
Helper utilities for the Discord bot.
"""
import re
import discord
from config import BotConfig

def is_valid_image_url(url):
    """Check if a URL points to an image file"""
    if not url:
        return False
    
    # Check common image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    url_lower = url.lower()
    
    # Check if URL ends with an image extension
    for ext in image_extensions:
        if url_lower.endswith(ext):
            return True
    
    # Check for image hosting patterns
    image_hosts = [
        r'i\.imgur\.com',
        r'cdn\.discordapp\.com\/attachments',
        r'media\.discordapp\.net',
        r'i\.redd\.it',
        r'images-ext-\d+\.discordapp\.net'
    ]
    
    for pattern in image_hosts:
        if re.search(pattern, url_lower):
            return True
    
    return False

def format_order_embed(order, user=None):
    """Format an order as an embed for display"""
    status_colors = {
        'pending_payment': discord.Color.orange(),
        'payment_received': discord.Color.blue(),
        'in_progress': discord.Color.purple(),
        'testing': discord.Color.gold(),
        'completed': discord.Color.green(),
        'cancelled': discord.Color.red()
    }
    
    status_emoji = {
        'pending_payment': '💰',
        'payment_received': '✅',
        'in_progress': '🔨',
        'testing': '🧪',
        'completed': '🎉',
        'cancelled': '❌'
    }
    
    status = order['status']
    
    # Create embed with color based on status
    embed = discord.Embed(
        title=f"Order #{order['order_id']}",
        color=status_colors.get(status, discord.Color.light_grey())
    )
    
    # Add order details
    embed.add_field(name="Bot Type", value=order['bot_type'].title(), inline=True)
    embed.add_field(name="Status", value=f"{status_emoji.get(status, '🔄')} {status.replace('_', ' ').title()}", inline=True)
    
    # Add price if available
    if order['price']:
        embed.add_field(name="Price", value=f"{order['price']} Robux", inline=True)
    else:
        embed.add_field(name="Price", value="Custom (To be determined)", inline=True)
    
    # Add features and notes
    embed.add_field(name="Features", value=order['features'], inline=False)
    
    if order['notes']:
        embed.add_field(name="Notes", value=order['notes'], inline=False)
    
    # Add timestamps
    embed.add_field(name="Created", value=f"<t:{int(order['created_at'].timestamp())}:R>", inline=True)
    embed.add_field(name="Last Updated", value=f"<t:{int(order['updated_at'].timestamp())}:R>", inline=True)
    
    # Set footer with customer info if user is provided
    if user:
        embed.set_footer(text=f"Customer: {user.name} | User ID: {user.id}")
    
    return embed
