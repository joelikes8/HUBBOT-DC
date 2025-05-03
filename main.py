"""
Discord Bot for managing custom bot requests with Robux payments.
This is the main entry point for the bot and Flask web application.
"""
import os
import logging
import threading
import asyncio
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from bot import setup_bot
from database import Database

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")  # Set a default for development
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db = SQLAlchemy(app)

# Discord bot instance
bot_instance = None

# Setup routes
@app.route('/')
def home():
    return render_template('index.html')

# Helper function to run async code in sync context
def run_async(coroutine):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()

# Map status to bootstrap color
def get_status_color(status):
    status_colors = {
        'pending_payment': 'warning',
        'payment_received': 'info',
        'in_progress': 'primary', 
        'testing': 'secondary',
        'completed': 'success',
        'cancelled': 'danger'
    }
    return status_colors.get(status, 'secondary')

# Format order for display
def format_order(order_data):
    return {
        'order_id': order_data['order_id'],
        'bot_type': order_data['bot_type'].title(),
        'status': order_data['status'].replace('_', ' ').title(),
        'status_color': get_status_color(order_data['status']),
        'features': order_data['features'],
        'created_at': order_data['created_at'].strftime('%Y-%m-%d %H:%M')
    }

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    user_id = request.args.get('user_id') or (request.form.get('user_id') if request.method == 'POST' else None)
    error = None
    user_info = None
    orders = []
    
    if user_id:
        try:
            # Convert user_id to integer
            user_id = int(user_id)
            
            # Get user info and orders
            user_info = run_async(Database.get_user(user_id))
            
            if not user_info:
                # Create a new user if not found
                user_info = run_async(Database.create_user(user_id))
            
            # Get user's orders
            orders_data = run_async(Database.get_user_orders(user_id))
            
            # Format orders for display
            for order_data in orders_data:
                orders.append(format_order(order_data))
            
        except ValueError:
            error = "Invalid Discord User ID format. Please enter a valid ID."
        except Exception as e:
            logger.error(f"Error fetching user data: {e}", exc_info=True)
            error = "There was an error loading your data. Please try again later."
    
    return render_template('dashboard.html', user_id=user_id, user_info=user_info, orders=orders, error=error)

@app.route('/order-status', methods=['GET', 'POST'])
def order_status_page():
    error = None
    order = None
    
    # Check if we're getting an order ID from query parameters
    order_id = request.args.get('id')
    
    # Or from form submission
    if request.method == 'POST':
        order_id = request.form.get('order_id')
    
    if order_id:
        try:
            # Get the order data
            order_data = run_async(Database.get_order(order_id))
            
            if not order_data:
                error = f"No order found with ID: {order_id}"
            else:
                # Format the order for display
                order = format_order(order_data)
        except Exception as e:
            logger.error(f"Error fetching order: {e}", exc_info=True)
            error = "There was an error fetching the order data. Please try again later."
    
    return render_template('order_status.html', error=error, order=order)

@app.route('/api/bot-status')
def bot_status():
    global bot_instance
    if bot_instance and bot_instance.is_ready():
        return jsonify({
            'status': 'online',
            'guilds': len(bot_instance.guilds),
            'users': sum(guild.member_count for guild in bot_instance.guilds)
        })
    return jsonify({'status': 'offline'})

# Run the bot in a separate thread
def run_bot():
    global bot_instance
    logger.info("Bot thread started, setting up async loop")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Get the token
        token = os.environ.get("DISCORD_TOKEN")
        logger.info(f"DISCORD_TOKEN exists: {token is not None and token != ''}")
        if not token:
            logger.error("DISCORD_TOKEN is not set or is empty")
            return
            
        logger.info(f"Attempting to start Discord bot with token starting with: {token[:5]}...")
        
        # Setup the bot
        logger.info("Calling setup_bot() function")
        bot_instance = setup_bot()
        logger.info(f"Bot instance created: {bot_instance is not None}")
        
        # Initialize database connection pool and set up tables
        logger.info("Creating database connection pool and initializing tables")
        try:
            # Create the pool
            loop.run_until_complete(Database.create_pool())
            # Explicitly set up the database tables
            loop.run_until_complete(Database.setup_database())
            logger.info("Database connection pool created successfully")
        except Exception as db_error:
            logger.error(f"Failed to create database connection pool: {db_error}", exc_info=True)
            return
        
        # Connect to Discord
        logger.info("Connecting to Discord...")
        bot_instance.run(token)
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
    finally:
        logger.info("Bot thread shutting down, closing async loop")
        loop.close()

# Start the bot thread
# This code will run when imported by gunicorn
# Check if DISCORD_TOKEN is set
if not os.environ.get("DISCORD_TOKEN"):
    logger.error("DISCORD_TOKEN environment variable not set. Bot will not start.")
else:
    # Start bot in a thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("Bot thread started")

# Start the Flask app if run directly
if __name__ == "__main__":
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
