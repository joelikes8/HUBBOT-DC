"""
Database management module for the Discord bot.
Handles connections to PostgreSQL and data operations.
"""
import os
import logging
import asyncio
import asyncpg
from config import BotConfig

logger = logging.getLogger(__name__)

class Database:
    """Database manager for PostgreSQL interactions"""
    _instance = None
    _pool = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one database connection pool exists"""
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    async def create_pool(cls):
        """Create connection pool to PostgreSQL"""
        if cls._pool is None:
            try:
                import asyncio
                # Get current event loop
                current_loop = asyncio.get_event_loop()
                logger.info(f"Creating database pool on event loop: {id(current_loop)}")
                
                cls._pool = await asyncpg.create_pool(
                    dsn=BotConfig.DATABASE_URL,
                    min_size=1,
                    max_size=10,
                    command_timeout=60,
                    loop=current_loop
                )
                logger.info("Database connection pool established")
                # Don't call setup_database here to avoid circular dependency
                # It will be called explicitly after pool creation
            except Exception as e:
                logger.error(f"Failed to create database connection pool: {e}", exc_info=True)
                raise
        return cls._pool
    
    @classmethod
    async def get_pool(cls):
        """Get the connection pool, creating it if needed"""
        try:
            import asyncio
            # Get the current event loop
            current_loop = asyncio.get_event_loop()
            
            if cls._pool is None:
                logger.info("Creating new database pool")
                await cls.create_pool()
            elif hasattr(cls._pool, 'closed'):
                if cls._pool.closed():
                    logger.warning("Detected closed pool, creating a new one")
                    cls._pool = None
                    await cls.create_pool()
            else:
                # Just in case the pool object doesn't have the expected methods
                logger.warning("Pool object has unexpected interface, proceeding with current pool")
            
            # Check if the pool's loop matches the current loop
            pool_loop = cls._pool._loop if hasattr(cls._pool, '_loop') else None
            if pool_loop is not None and pool_loop != current_loop:
                logger.warning("Pool is attached to a different event loop. Creating a new pool for the current loop.")
                cls._pool = None
                await cls.create_pool()
                
            return cls._pool
        except Exception as e:
            logger.error(f"Error in get_pool: {e}", exc_info=True)
            # If there was an error, try to create a fresh pool
            cls._pool = None
            await cls.create_pool()
            return cls._pool
    
    @classmethod
    async def close_pool(cls):
        """Close the connection pool"""
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None
            logger.info("Database connection pool closed")
    
    @classmethod
    async def setup_database(cls):
        """Set up the database tables if they don't exist"""
        # Make sure we have a valid pool
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            # Create users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    discord_id BIGINT UNIQUE NOT NULL,
                    roblox_username VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    orders_count INT DEFAULT 0,
                    activity_points INT DEFAULT 0
                )
            ''')
            
            # Create orders table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    order_id VARCHAR(20) UNIQUE NOT NULL,
                    user_id BIGINT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
                    status VARCHAR(50) DEFAULT 'pending_payment',
                    bot_type VARCHAR(50) NOT NULL,
                    features TEXT NOT NULL,
                    notes TEXT,
                    price INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create payments table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    order_id VARCHAR(20) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
                    proof_url TEXT,
                    status VARCHAR(50) DEFAULT 'pending',
                    approved_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create giveaways table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS giveaways (
                    id SERIAL PRIMARY KEY,
                    message_id BIGINT UNIQUE NOT NULL,
                    channel_id BIGINT NOT NULL,
                    creator_id BIGINT NOT NULL,
                    prize TEXT NOT NULL,
                    winner_count INT DEFAULT 1,
                    end_time TIMESTAMP NOT NULL,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create giveaway_entries table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS giveaway_entries (
                    id SERIAL PRIMARY KEY,
                    giveaway_id INT REFERENCES giveaways(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(giveaway_id, user_id)
                )
            ''')
            
            # Create tips table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_tips (
                    id SERIAL PRIMARY KEY,
                    tip_text TEXT NOT NULL,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create feedback table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    feedback_type VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            logger.info("Database tables created successfully")
    
    # User methods
    @classmethod
    async def get_user(cls, discord_id):
        """Get a user by Discord ID"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow('SELECT * FROM users WHERE discord_id = $1', discord_id)
    
    @classmethod
    async def create_user(cls, discord_id, roblox_username=None):
        """Create a new user"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow('''
                INSERT INTO users (discord_id, roblox_username) 
                VALUES ($1, $2) 
                ON CONFLICT (discord_id) 
                DO UPDATE SET roblox_username = $2
                RETURNING *
            ''', discord_id, roblox_username)
    
    @classmethod
    async def link_roblox(cls, discord_id, roblox_username):
        """Link a Discord user to a Roblox username"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow('''
                UPDATE users SET roblox_username = $2
                WHERE discord_id = $1
                RETURNING *
            ''', discord_id, roblox_username)
    
    @classmethod
    async def increment_activity(cls, discord_id, points=1):
        """Increment a user's activity points"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.execute('''
                UPDATE users 
                SET activity_points = activity_points + $2
                WHERE discord_id = $1
            ''', discord_id, points)
    
    @classmethod
    async def get_leaderboard(cls, limit=10):
        """Get the top users by activity points"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch('''
                SELECT * FROM users
                ORDER BY activity_points DESC
                LIMIT $1
            ''', limit)
    
    # Order methods
    @classmethod
    async def create_order(cls, order_id, user_id, bot_type, features, notes=None, price=None):
        """Create a new order"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Check if user exists, create if not
                user = await cls.get_user(user_id)
                if not user:
                    await cls.create_user(user_id)
                
                # Create the order
                order = await conn.fetchrow('''
                    INSERT INTO orders (order_id, user_id, bot_type, features, notes, price)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                ''', order_id, user_id, bot_type, features, notes, price)
                
                # Update user's order count
                await conn.execute('''
                    UPDATE users
                    SET orders_count = orders_count + 1
                    WHERE discord_id = $1
                ''', user_id)
                
                return order
    
    @classmethod
    async def get_order(cls, order_id):
        """Get an order by ID"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow('SELECT * FROM orders WHERE order_id = $1', order_id)
    
    @classmethod
    async def get_user_orders(cls, user_id):
        """Get all orders for a user"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch('''
                SELECT * FROM orders 
                WHERE user_id = $1
                ORDER BY created_at DESC
            ''', user_id)
    
    @classmethod
    async def update_order_status(cls, order_id, status):
        """Update an order's status"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow('''
                UPDATE orders
                SET status = $2, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = $1
                RETURNING *
            ''', order_id, status)
    
    @classmethod
    async def cancel_order(cls, order_id):
        """Cancel an order if work hasn't started"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            # Check if the order is in a cancellable state
            order = await conn.fetchrow('''
                SELECT * FROM orders 
                WHERE order_id = $1 AND status IN ('pending_payment', 'payment_received')
            ''', order_id)
            
            if not order:
                return None
            
            # Cancel the order
            return await conn.fetchrow('''
                UPDATE orders
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = $1
                RETURNING *
            ''', order_id)
    
    # Payment methods
    @classmethod
    async def submit_payment(cls, order_id, proof_url):
        """Submit a payment proof for an order"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            # Check if order exists and is in pending_payment status
            order = await conn.fetchrow('SELECT * FROM orders WHERE order_id = $1', order_id)
            if not order:
                return None
                
            # First check if a payment record already exists
            existing_payment = await conn.fetchrow('SELECT * FROM payments WHERE order_id = $1', order_id)
            
            if existing_payment:
                # Update existing payment record
                payment = await conn.fetchrow('''
                    UPDATE payments 
                    SET proof_url = $2, status = 'pending', updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = $1
                    RETURNING *
                ''', order_id, proof_url)
            else:
                # Create new payment record
                payment = await conn.fetchrow('''
                    INSERT INTO payments (order_id, proof_url)
                    VALUES ($1, $2)
                    RETURNING *
                ''', order_id, proof_url)
            
            # Update order status
            await conn.execute('''
                UPDATE orders
                SET status = 'pending_payment', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = $1
            ''', order_id)
            
            return payment
    
    @classmethod
    async def approve_payment(cls, order_id, approved_by):
        """Approve a payment for an order"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Update payment status
                payment = await conn.fetchrow('''
                    UPDATE payments
                    SET status = 'approved', approved_by = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = $1
                    RETURNING *
                ''', order_id, approved_by)
                
                if not payment:
                    return None
                
                # Update order status
                await conn.execute('''
                    UPDATE orders
                    SET status = 'payment_received', updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = $1
                ''', order_id)
                
                return payment
    
    # Giveaway methods
    @classmethod
    async def create_giveaway(cls, message_id, channel_id, creator_id, prize, winner_count, end_time):
        """Create a new giveaway"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow('''
                INSERT INTO giveaways (message_id, channel_id, creator_id, prize, winner_count, end_time)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            ''', message_id, channel_id, creator_id, prize, winner_count, end_time)
    
    @classmethod
    async def enter_giveaway(cls, giveaway_id, user_id):
        """Enter a user into a giveaway"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            try:
                return await conn.fetchrow('''
                    INSERT INTO giveaway_entries (giveaway_id, user_id)
                    VALUES ($1, $2)
                    RETURNING *
                ''', giveaway_id, user_id)
            except asyncpg.UniqueViolationError:
                # User already entered
                return None
    
    @classmethod
    async def get_active_giveaways(cls):
        """Get all active giveaways"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch('''
                SELECT * FROM giveaways
                WHERE status = 'active' AND end_time > CURRENT_TIMESTAMP
            ''')
    
    @classmethod
    async def get_giveaway_entries(cls, giveaway_id):
        """Get all entries for a giveaway"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch('''
                SELECT * FROM giveaway_entries
                WHERE giveaway_id = $1
            ''', giveaway_id)
    
    @classmethod
    async def complete_giveaway(cls, giveaway_id, winner_ids):
        """Mark a giveaway as completed and record winners"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            await conn.execute('''
                UPDATE giveaways
                SET status = 'completed', winner_ids = $2
                WHERE id = $1
            ''', giveaway_id, winner_ids)
    
    # Daily tips methods
    @classmethod
    async def add_tip(cls, tip_text, created_by):
        """Add a new daily tip"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow('''
                INSERT INTO daily_tips (tip_text, created_by)
                VALUES ($1, $2)
                RETURNING *
            ''', tip_text, created_by)
    
    @classmethod
    async def get_random_tip(cls):
        """Get a random daily tip"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow('SELECT * FROM daily_tips ORDER BY RANDOM() LIMIT 1')
    
    # Feedback methods
    @classmethod
    async def submit_feedback(cls, user_id, feedback_type, content):
        """Submit user feedback"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow('''
                INSERT INTO feedback (user_id, feedback_type, content)
                VALUES ($1, $2, $3)
                RETURNING *
            ''', user_id, feedback_type, content)
    
    @classmethod
    async def get_pending_feedback(cls):
        """Get all pending feedback"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch('''
                SELECT * FROM feedback
                WHERE status = 'pending'
                ORDER BY created_at ASC
            ''')
    
    @classmethod
    async def update_feedback_status(cls, feedback_id, status):
        """Update feedback status"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow('''
                UPDATE feedback
                SET status = $2
                WHERE id = $1
                RETURNING *
            ''', feedback_id, status)
