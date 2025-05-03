"""
Admin Cog for handling administrative commands.
These commands are only accessible to staff and administrators.
"""
import logging
import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from config import BotConfig

logger = logging.getLogger(__name__)

class Admin(commands.Cog):
    """Administrative commands for staff and admins"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def is_staff(self, interaction: discord.Interaction) -> bool:
        """Check if the user has a staff or admin role"""
        return any(role.id in (BotConfig.ADMIN_ROLE_ID, BotConfig.STAFF_ROLE_ID) 
                  for role in interaction.user.roles)
    
    @app_commands.command(name="update-status", description="Update the status of an order")
    @app_commands.describe(
        order_id="The order ID to update",
        status="New status for the order"
    )
    async def update_status(self, interaction: discord.Interaction, order_id: str, status: str):
        """Update the status of an order (staff only)"""
        # Check if user is staff
        if not await self.is_staff(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        # Validate status
        valid_statuses = BotConfig.ORDER_STATUSES
        if status not in valid_statuses:
            await interaction.response.send_message(
                f"Invalid status. Please choose from: {', '.join(valid_statuses)}",
                ephemeral=True
            )
            return
        
        try:
            # Update the order status
            updated_order = await Database.update_order_status(order_id, status)
            
            if not updated_order:
                await interaction.response.send_message(
                    f"No order found with ID: {order_id}",
                    ephemeral=True
                )
                return
            
            # Create a confirmation embed
            embed = discord.Embed(
                title="Order Status Updated",
                description=f"Order {order_id} has been updated to status: **{status}**",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Notify the customer
            try:
                user = self.bot.get_user(updated_order['user_id'])
                if user:
                    user_embed = discord.Embed(
                        title="Order Status Update",
                        description=f"Your order has been updated to: **{status}**",
                        color=discord.Color.blue()
                    )
                    user_embed.add_field(name="Order ID", value=order_id, inline=True)
                    user_embed.add_field(name="Updated By", value=interaction.user.name, inline=True)
                    user_embed.set_footer(text="Use /order-status to check full details")
                    
                    await user.send(embed=user_embed)
            except Exception as e:
                logger.error(f"Error notifying user about status update: {e}")
                # Continue even if notification fails
        
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            await interaction.response.send_message(
                "There was an error updating the order status. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="approve-payment", description="Approve a payment for an order")
    @app_commands.describe(order_id="The order ID to approve payment for")
    async def approve_payment(self, interaction: discord.Interaction, order_id: str):
        """Approve a payment for an order (staff only)"""
        # Check if user is staff
        if not await self.is_staff(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        try:
            # Approve the payment
            payment = await Database.approve_payment(order_id, interaction.user.id)
            
            if not payment:
                await interaction.response.send_message(
                    f"No payment found for order: {order_id}",
                    ephemeral=True
                )
                return
            
            # Create a confirmation embed
            embed = discord.Embed(
                title="Payment Approved",
                description=f"Payment for Order {order_id} has been approved.",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Notify the customer
            order = await Database.get_order(order_id)
            if order:
                try:
                    user = self.bot.get_user(order['user_id'])
                    if user:
                        user_embed = discord.Embed(
                            title="Payment Approved",
                            description=f"Your payment for Order {order_id} has been approved! Work on your bot will begin soon.",
                            color=discord.Color.green()
                        )
                        user_embed.set_footer(text="Use /order-status to check progress updates")
                        
                        await user.send(embed=user_embed)
                except Exception as e:
                    logger.error(f"Error notifying user about payment approval: {e}")
                    # Continue even if notification fails
        
        except Exception as e:
            logger.error(f"Error approving payment: {e}")
            await interaction.response.send_message(
                "There was an error approving the payment. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="reject-payment", description="Reject a payment for an order")
    @app_commands.describe(
        order_id="The order ID to reject payment for",
        reason="Reason for rejection"
    )
    async def reject_payment(self, interaction: discord.Interaction, order_id: str, reason: str):
        """Reject a payment for an order (staff only)"""
        # Check if user is staff
        if not await self.is_staff(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        try:
            # Get the payment and order
            order = await Database.get_order(order_id)
            
            if not order:
                await interaction.response.send_message(
                    f"No order found with ID: {order_id}",
                    ephemeral=True
                )
                return
            
            # Create a confirmation embed
            embed = discord.Embed(
                title="Payment Rejected",
                description=f"Payment for Order {order_id} has been rejected.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            # Notify the customer
            try:
                user = self.bot.get_user(order['user_id'])
                if user:
                    user_embed = discord.Embed(
                        title="Payment Rejected",
                        description=f"Your payment for Order {order_id} has been rejected.",
                        color=discord.Color.red()
                    )
                    user_embed.add_field(name="Reason", value=reason, inline=False)
                    user_embed.add_field(
                        name="Next Steps",
                        value="Please submit a new payment proof using `/submit-payment` or contact support for assistance.",
                        inline=False
                    )
                    
                    await user.send(embed=user_embed)
            except Exception as e:
                logger.error(f"Error notifying user about payment rejection: {e}")
                # Continue even if notification fails
        
        except Exception as e:
            logger.error(f"Error rejecting payment: {e}")
            await interaction.response.send_message(
                "There was an error rejecting the payment. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="add-tip", description="Add a new daily tip to the database")
    @app_commands.describe(tip_text="The text of the tip to add")
    async def add_tip(self, interaction: discord.Interaction, tip_text: str):
        """Add a new daily tip (staff only)"""
        # Check if user is staff
        if not await self.is_staff(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        try:
            # Add the tip to the database
            await Database.add_tip(tip_text, interaction.user.id)
            
            # Create a confirmation embed
            embed = discord.Embed(
                title="Daily Tip Added",
                description="Your tip has been added to the database and will be shown in the daily tip rotation.",
                color=discord.Color.green()
            )
            embed.add_field(name="Tip", value=tip_text, inline=False)
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            logger.error(f"Error adding daily tip: {e}")
            await interaction.response.send_message(
                "There was an error adding the daily tip. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="view-feedback", description="View all pending feedback and suggestions")
    async def view_feedback(self, interaction: discord.Interaction):
        """View all pending feedback (staff only)"""
        # Check if user is staff
        if not await self.is_staff(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        try:
            # Get all pending feedback
            feedback_items = await Database.get_pending_feedback()
            
            if not feedback_items:
                await interaction.response.send_message(
                    "There is no pending feedback at this time.",
                    ephemeral=True
                )
                return
            
            # Create embed pages (max 5 items per page)
            pages = []
            for i in range(0, len(feedback_items), 5):
                chunk = feedback_items[i:i+5]
                
                embed = discord.Embed(
                    title="Pending Feedback",
                    description=f"Page {len(pages) + 1}/{(len(feedback_items) + 4) // 5}",
                    color=discord.Color.blue()
                )
                
                for item in chunk:
                    user = self.bot.get_user(item['user_id'])
                    username = user.name if user else f"User {item['user_id']}"
                    
                    embed.add_field(
                        name=f"{item['feedback_type'].title()} from {username}",
                        value=f"**ID:** {item['id']}\n**Content:** {item['content']}\n**Date:** {item['created_at'].strftime('%Y-%m-%d %H:%M')}",
                        inline=False
                    )
                
                pages.append(embed)
            
            # Send the first page
            await interaction.response.send_message(embed=pages[0])
            
            # Add pagination in a future update if needed
        
        except Exception as e:
            logger.error(f"Error viewing feedback: {e}")
            await interaction.response.send_message(
                "There was an error retrieving feedback. Please try again later.",
                ephemeral=True
            )

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(Admin(bot))
