"""Order Management Cog for handling bot order commands.
Includes commands for creating orders, checking status, submitting payments, and more.
"""
import logging
import random
import string
import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from config import BotConfig
from utils.helpers import is_valid_image_url, format_order_embed

logger = logging.getLogger(__name__)

class OrderManagement(commands.Cog):
    """Order management commands for bot services"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def generate_order_id(self, length=8):
        """Generate a unique order ID"""
        chars = string.ascii_uppercase + string.digits
        return 'ORD-' + ''.join(random.choice(chars) for _ in range(length))
    
    @app_commands.command(name="order", description="Begin a custom bot request")
    @app_commands.describe(
        bot_type="Type of bot you want (basic, standard, premium, custom)",
        features="Comma-separated list of features you want in your bot",
        notes="Additional notes or requirements (optional)"
    )
    async def order(self, interaction: discord.Interaction, bot_type: str, features: str, notes: str = None):
        """Begin a custom bot request with features, type, and notes"""
        # Use immediate response instead of defer for more reliable interaction handling
        try:
            await interaction.response.send_message("Checking your account and processing your order...")
        except Exception as e:
            logger.error(f"Failed to acknowledge interaction: {e}", exc_info=True)
            try:
                await interaction.response.defer(ephemeral=False)
            except Exception:
                # If we can't respond at all, just log it and let the error show
                logger.error("Could not respond to interaction at all!")
                return
                
        try:
            # First check if the user has linked their Roblox account
            user_id = interaction.user.id
            
            # Create a function to handle all the database operations
            async def process_order():
                try:
                    # First check if user exists and has Roblox linked
                    user = await Database.get_user(user_id)
                    
                    # Check if the user has linked their Roblox account
                    if not user or not user.get('roblox_username'):
                        # User has not linked their Roblox account, create an embed explaining this requirement
                        embed = discord.Embed(
                            title="Roblox Account Required",
                            description="You need to link your Roblox account before placing an order.",
                            color=discord.Color.red()
                        )
                        embed.add_field(
                            name="Why is this needed?",
                            value="We need your Roblox username to process payments through Robux.",
                            inline=False
                        )
                        embed.add_field(
                            name="How to link your account",
                            value="Use the `/link` command with your Roblox username:\n`/link YourRobloxUsername`",
                            inline=False
                        )
                        embed.set_footer(text="After linking your account, you can place your order again.")
                        
                        try:
                            await interaction.edit_original_response(content="", embed=embed)
                        except Exception:
                            await interaction.followup.send(embed=embed)
                        return
                    
                    # Validate bot type
                    bot_type_lower = bot_type.lower()
                    valid_types = list(BotConfig.PRICING.keys())
                    
                    if bot_type_lower not in valid_types:
                        try:
                            await interaction.edit_original_response(
                                content=f"Invalid bot type. Please choose from: {', '.join(valid_types)}"
                            )
                        except Exception:
                            await interaction.followup.send(
                                f"Invalid bot type. Please choose from: {', '.join(valid_types)}"
                            )
                        return
                    
                    # Generate order ID
                    order_id = self.generate_order_id()
                    logger.info(f"Generated order ID: {order_id}")
                    
                    # Determine price
                    price = BotConfig.PRICING[bot_type_lower]["price"]
                    if isinstance(price, str):  # If price is "Custom"
                        price = None
                        
                    # Then create the order
                    logger.info(f"Creating order with ID {order_id} for user {interaction.user.id}")
                    order = await Database.create_order(
                        order_id=order_id,
                        user_id=interaction.user.id,
                        bot_type=bot_type_lower,
                        features=features,
                        notes=notes,
                        price=price
                    )
                    
                    logger.info(f"Order created successfully: {order_id}")
                    
                    # Create an embed for the order
                    embed = format_order_embed(order, interaction.user)
                    
                    # Add Roblox username to the embed
                    embed.add_field(
                        name="Roblox Username",
                        value=user.get('roblox_username', 'Unknown'),
                        inline=True
                    )
                    
                    # Send confirmation to the user with the updated info
                    try:
                        await interaction.edit_original_response(
                            content=f"Order #{order_id} has been submitted! Here are the details:",
                            embed=embed
                        )
                    except Exception:
                        await interaction.followup.send(
                            f"Order #{order_id} has been submitted! Here are the details:",
                            embed=embed
                        )
                    
                    # Notify staff in the orders channel if configured
                    if BotConfig.ORDER_CHANNEL_ID:
                        order_channel = self.bot.get_channel(BotConfig.ORDER_CHANNEL_ID)
                        if order_channel:
                            staff_embed = embed.copy()
                            staff_embed.add_field(
                                name="Action Required",
                                value="Please review this order and contact the customer for payment details.",
                                inline=False
                            )
                            await order_channel.send(f"New order from {interaction.user.mention}!", embed=staff_embed)
                            
                except Exception as e:
                    logger.error(f"Error in process_order: {e}", exc_info=True)
                    try:
                        await interaction.edit_original_response(
                            content="There was an error processing your order. Please try again later."
                        )
                    except Exception:
                        try:
                            await interaction.followup.send(
                                "There was an error processing your order. Please try again later."
                            )
                        except Exception:
                            logger.error("Could not send error message")
            
            # Start the database processing in a new task to avoid timeout
            import asyncio
            task = asyncio.create_task(process_order())
            # Log that we created the task
            logger.info(f"Created task for processing order: {task}")
            
        except Exception as e:
            logger.error(f"Error creating order: {e}", exc_info=True)
            try:
                await interaction.edit_original_response(
                    content="There was an error processing your order. Please try again later."
                )
            except Exception as follow_error:
                logger.error(f"Failed to send error message: {follow_error}")
                try:
                    await interaction.followup.send(
                        "There was an error processing your order. Please try again later."
                    )
                except Exception:
                    logger.error("Could not send error message")
                    pass
    
    @app_commands.command(name="order-status", description="Check the status of your bot order")
    @app_commands.describe(order_id="The order ID you want to check")
    async def order_status(self, interaction: discord.Interaction, order_id: str):
        """Check the live status of your bot request"""
        # Use immediate response instead of defer for more reliable interaction handling
        try:
            await interaction.response.send_message("Checking order status, please wait a moment...")
        except Exception as e:
            logger.error(f"Failed to acknowledge interaction: {e}", exc_info=True)
            try:
                await interaction.response.defer(ephemeral=False)
            except Exception:
                # If we can't respond at all, just log it and let the error show
                logger.error("Could not respond to interaction at all!")
                return
        
        try:
            # Create a function to handle the database operations
            async def check_order_status():
                try:
                    # Get the order from the database
                    order = await Database.get_order(order_id)
                    
                    if not order:
                        try:
                            await interaction.edit_original_response(
                                content=f"No order found with ID: {order_id}"
                            )
                        except Exception:
                            await interaction.followup.send(
                                f"No order found with ID: {order_id}"
                            )
                        return
                    
                    # Check if the user is the order owner or staff
                    is_staff = any(role.id in (BotConfig.ADMIN_ROLE_ID, BotConfig.STAFF_ROLE_ID) 
                                   for role in interaction.user.roles)
                    
                    if order['user_id'] != interaction.user.id and not is_staff:
                        try:
                            await interaction.edit_original_response(
                                content="You don't have permission to view this order."
                            )
                        except Exception:
                            await interaction.followup.send(
                                "You don't have permission to view this order."
                            )
                        return
                    
                    # Get the user's Roblox username
                    user = await Database.get_user(order['user_id'])
                    
                    # Create and send the order embed
                    embed = format_order_embed(order, interaction.user)
                    
                    # Add Roblox username to the embed if available
                    if user and user.get('roblox_username'):
                        embed.add_field(
                            name="Roblox Username",
                            value=user.get('roblox_username'),
                            inline=True
                        )
                    
                    try:
                        await interaction.edit_original_response(
                            content=f"Status for Order {order_id}:",
                            embed=embed
                        )
                    except Exception:
                        await interaction.followup.send(
                            f"Status for Order {order_id}:",
                            embed=embed
                        )
                        
                except Exception as e:
                    logger.error(f"Error in check_order_status: {e}", exc_info=True)
                    try:
                        await interaction.edit_original_response(
                            content="There was an error checking your order status. Please try again later."
                        )
                    except Exception:
                        await interaction.followup.send(
                            "There was an error checking your order status. Please try again later."
                        )
            
            # Start the database processing in a new task to avoid timeout
            import asyncio
            task = asyncio.create_task(check_order_status())
            # Log that we created the task
            logger.info(f"Created task for checking order status: {task}")
        
        except Exception as e:
            logger.error(f"Error checking order status: {e}", exc_info=True)
            try:
                await interaction.edit_original_response(
                    content="There was an error checking your order status. Please try again later."
                )
            except Exception:
                try:
                    await interaction.followup.send(
                        "There was an error checking your order status. Please try again later."
                    )
                except Exception:
                    logger.error("Could not send error message")
    
    @app_commands.command(name="submit-payment", description="Submit payment proof for your order")
    @app_commands.describe(
        order_id="The order ID you're submitting payment for",
        proof="Upload a screenshot as proof of Robux payment"
    )
    async def submit_payment(self, interaction: discord.Interaction, order_id: str, proof: discord.Attachment):
        """Upload a screenshot as proof of Robux payment"""
        # Use immediate response instead of defer for more reliable interaction handling
        try:
            await interaction.response.send_message("Processing your payment submission, please wait...")
        except Exception as e:
            logger.error(f"Failed to acknowledge interaction: {e}", exc_info=True)
            try:
                await interaction.response.defer(ephemeral=False)
            except Exception:
                # If we can't respond at all, just log it and let the error show
                logger.error("Could not respond to interaction at all!")
                return
        
        # Capture attachment data immediately to avoid issues with the task
        proof_url = proof.url if proof else None
        content_type = getattr(proof, 'content_type', None)
        
        # Do validation outside of the task
        if not proof_url or not content_type or not content_type.startswith('image/'):
            try:
                await interaction.edit_original_response(content="Please upload an image file as payment proof.")
            except Exception:
                try:
                    await interaction.followup.send("Please upload an image file as payment proof.")
                except Exception:
                    logger.error("Could not respond with validation error")
            return
        
        try:    
            # Create a function to handle the database operations
            async def process_payment():
                try:
                    logger.info(f"Processing payment for order_id: {order_id}, proof_url: {proof_url}")
                    
                    # Check if the order exists
                    order = await Database.get_order(order_id)
                    
                    if not order:
                        try:
                            await interaction.edit_original_response(content=f"No order found with ID: {order_id}")
                        except Exception:
                            await interaction.followup.send(f"No order found with ID: {order_id}")
                        return
                    
                    # Check if the user is the order owner
                    if order['user_id'] != interaction.user.id:
                        try:
                            await interaction.edit_original_response(content="You can only submit payment for your own orders.")
                        except Exception:
                            await interaction.followup.send("You can only submit payment for your own orders.")
                        return
                    
                    # Record the payment submission
                    payment_result = await Database.submit_payment(order_id, proof_url)
                    
                    if not payment_result:
                        try:
                            await interaction.edit_original_response(content="There was an error recording your payment. Please try again.")
                        except Exception:
                            await interaction.followup.send("There was an error recording your payment. Please try again.")
                        return
                    
                    # Create a confirmation embed with bot type and features information
                    embed = discord.Embed(
                        title="Payment Submitted",
                        description=f"Your payment proof for Order {order_id} has been submitted for review.",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="Order ID", value=order_id, inline=True)
                    embed.add_field(name="Status", value="Payment Review Pending", inline=True)
                    
                    # Add bot type and features information
                    bot_type = order['bot_type'].title() if order['bot_type'] else 'Custom'
                    embed.add_field(name="Bot Type", value=bot_type, inline=True)
                    
                    if order['features']:
                        features = order['features']
                        # Truncate if too long
                        if len(features) > 200:
                            features = features[:197] + '...'
                        embed.add_field(name="Features", value=features, inline=False)
                    
                    # Add price if available
                    if order['price'] is not None:
                        embed.add_field(name="Price", value=f"{order['price']} Robux", inline=True)
                    
                    embed.set_image(url=proof_url)
                    embed.set_footer(text="A staff member will review your payment soon.")
                    
                    try:
                        await interaction.edit_original_response(content="", embed=embed)
                    except Exception:
                        await interaction.followup.send(embed=embed)
                    
                    # Notify staff in the orders channel if configured
                    if BotConfig.ORDER_CHANNEL_ID:
                        order_channel = self.bot.get_channel(BotConfig.ORDER_CHANNEL_ID)
                        if order_channel:
                            staff_embed = embed.copy()
                            staff_embed.title = "Payment Proof Submitted"
                            staff_embed.description = f"Payment proof submitted by {interaction.user.mention} for Order {order_id}."
                            
                            # Add order details from above to make it easier for staff to see what they're approving
                            staff_embed.add_field(
                                name="Bot Type",
                                value=bot_type,
                                inline=True
                            )
                            
                            if order['price'] is not None:
                                staff_embed.add_field(
                                    name="Price",
                                    value=f"{order['price']} Robux",
                                    inline=True
                                )
                            
                            staff_embed.add_field(
                                name="Action Required",
                                value="Please review this payment proof and use `/approve-payment` or `/reject-payment` to process.",
                                inline=False
                            )
                            await order_channel.send(embed=staff_embed)
                except Exception as e:
                    logger.error(f"Error in process_payment: {e}", exc_info=True)
                    try:
                        await interaction.edit_original_response(content="There was an error submitting your payment. Please try again later.")
                    except Exception:
                        try:
                            await interaction.followup.send("There was an error submitting your payment. Please try again later.")
                        except Exception:
                            logger.error("Could not send error message")
            
            # Start the database processing in a new task to avoid timeout
            import asyncio
            task = asyncio.create_task(process_payment())
            # Log that we created the task
            logger.info(f"Created task for processing payment: {task}")
        
        except Exception as e:
            logger.error(f"Error submitting payment: {e}", exc_info=True)
            try:
                await interaction.edit_original_response(content="There was an error submitting your payment. Please try again later.")
            except Exception:
                try:
                    await interaction.followup.send("There was an error submitting your payment. Please try again later.")
                except Exception:
                    logger.error("Could not send error message")

    
    @app_commands.command(name="cancel-order", description="Cancel your bot order")
    @app_commands.describe(order_id="The order ID you want to cancel")
    async def cancel_order(self, interaction: discord.Interaction, order_id: str):
        """Cancel your order if work hasn't started"""
        # Acknowledge the interaction immediately to prevent timeout
        await interaction.response.defer(ephemeral=False)
        
        try:
            # Send a processing message to avoid timeout
            await interaction.followup.send(f"Processing request to cancel Order ID: {order_id}...")
            
            # Create a function to handle the database operations
            async def process_cancellation():
                try:
                    # Get the order from the database
                    order = await Database.get_order(order_id)
                    
                    if not order:
                        await interaction.followup.send(
                            f"No order found with ID: {order_id}",
                            ephemeral=True
                        )
                        return
                    
                    # Check if the user is the order owner
                    if order['user_id'] != interaction.user.id:
                        await interaction.followup.send(
                            "You can only cancel your own orders.",
                            ephemeral=True
                        )
                        return
                    
                    # Check if the order can be cancelled
                    if order['status'] not in ('pending_payment', 'payment_received'):
                        await interaction.followup.send(
                            "This order cannot be cancelled because work has already begun. Please contact staff for assistance.",
                            ephemeral=True
                        )
                        return
                    
                    # Cancel the order
                    cancelled_order = await Database.cancel_order(order_id)
                    
                    if not cancelled_order:
                        await interaction.followup.send(
                            "There was an error cancelling your order. Please try again later.",
                            ephemeral=True
                        )
                        return
                    
                    # Create a confirmation embed
                    embed = discord.Embed(
                        title="Order Cancelled",
                        description=f"Your order {order_id} has been cancelled.",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Order ID", value=order_id, inline=True)
                    embed.add_field(name="Status", value="Cancelled", inline=True)
                    embed.set_footer(text="Thank you for your interest. We hope to serve you in the future.")
                    
                    await interaction.followup.send(embed=embed)
                    
                    # Notify staff in the orders channel if configured
                    if BotConfig.ORDER_CHANNEL_ID:
                        order_channel = self.bot.get_channel(BotConfig.ORDER_CHANNEL_ID)
                        if order_channel:
                            staff_embed = embed.copy()
                            staff_embed.description = f"Order {order_id} has been cancelled by {interaction.user.mention}."
                            await order_channel.send(embed=staff_embed)
                except Exception as e:
                    logger.error(f"Error in process_cancellation: {e}", exc_info=True)
                    await interaction.followup.send(
                        "There was an error cancelling your order. Please try again later.",
                        ephemeral=True
                    )
            
            # Start the database processing in a new task to avoid timeout
            import asyncio
            asyncio.create_task(process_cancellation())
        
        except Exception as e:
            logger.error(f"Error cancelling order: {e}", exc_info=True)
            await interaction.followup.send(
                "There was an error cancelling your order. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="pricing", description="View pricing for custom bot services")
    async def pricing(self, interaction: discord.Interaction):
        """Display pricing information for bot services"""
        embed = discord.Embed(
            title="Bot Service Pricing",
            description="Here are our current pricing options for custom Discord bots. All prices are in Robux.",
            color=discord.Color.gold()
        )
        
        for bot_type, info in BotConfig.PRICING.items():
            embed.add_field(
                name=f"{bot_type.title()} - {info['price']} Robux",
                value=info['description'],
                inline=False
            )
        
        embed.add_field(
            name="Payment Process",
            value="Payment is made through Robux via a gamepass. Use `/link` to connect your Roblox account, then use `/submit-payment` after making your purchase.",
            inline=False
        )
        
        embed.set_footer(text="For additional questions, use /support to contact our team.")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="link", description="Link your Discord account to your Roblox username")
    @app_commands.describe(roblox_username="Your Roblox username")
    async def link(self, interaction: discord.Interaction, roblox_username: str):
        """Link a Discord account to a Roblox username"""
        # Use immediate response instead of defer for more reliable interaction handling
        try:
            await interaction.response.send_message(f"Linking your Discord account to Roblox username: {roblox_username}...")
        except Exception as e:
            logger.error(f"Failed to acknowledge interaction: {e}", exc_info=True)
            try:
                await interaction.response.defer(ephemeral=False)
            except Exception:
                # If we can't respond at all, just log it and let the error show
                logger.error("Could not respond to interaction at all!")
                return
        
        try:
            # Create a function to handle the database operations
            async def process_link():
                try:
                    logger.info(f"Linking Discord ID: {interaction.user.id} to Roblox username: {roblox_username}")
                    
                    # Update or create user in the database
                    user = await Database.link_roblox(interaction.user.id, roblox_username)
                    
                    if not user:
                        try:
                            await interaction.edit_original_response(content="Failed to link account. Please try again.")
                        except Exception:
                            await interaction.followup.send("Failed to link account. Please try again.")
                        return
                    
                    embed = discord.Embed(
                        title="Account Linked",
                        description=f"Your Discord account has been linked to Roblox username: **{roblox_username}**",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="This information will be used for order processing and payments.")
                    
                    try:
                        await interaction.edit_original_response(content="", embed=embed)
                    except Exception:
                        await interaction.followup.send(embed=embed)
                        
                except Exception as e:
                    logger.error(f"Error in process_link: {e}", exc_info=True)
                    try:
                        await interaction.edit_original_response(content="There was an error linking your account. Please try again later.")
                    except Exception:
                        try:
                            await interaction.followup.send("There was an error linking your account. Please try again later.")
                        except Exception:
                            logger.error("Could not send error message")
            
            # Start the database processing in a new task to avoid timeout
            import asyncio
            task = asyncio.create_task(process_link())
            # Log that we created the task
            logger.info(f"Created task for linking account: {task}")
        
        except Exception as e:
            logger.error(f"Error linking Roblox account: {e}", exc_info=True)
            try:
                await interaction.edit_original_response(content="There was an error linking your account. Please try again later.")
            except Exception:
                try:
                    await interaction.followup.send("There was an error linking your account. Please try again later.")
                except Exception:
                    logger.error("Could not send error message")

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(OrderManagement(bot))
