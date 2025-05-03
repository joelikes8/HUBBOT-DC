# HUBBOT-DC

A Discord bot for managing custom bot requests with Robux payment integration.

## Features

### Order Management
- `/order` - Begin a custom bot request with features, type, and notes
- `/order-status` - Check the live status of your bot request
- `/submit-payment` - Upload a screenshot as proof of Robux payment
- `/cancel-order` - Cancel your order if work hasn't started
- `/pricing` - Display pricing information for bot services
- `/link` - Link a Discord account to a Roblox username

### Community Engagement
- `/giveaway` - Start a giveaway for Robux, free bots, or perks
- `/daily-tip` - Get a random bot idea or helpful tip
- `/suggest` - Submit feedback or ideas for the server
- `/vote` - Get a link to vote for the server or bot
- `/leaderboard` - See the top buyers or most active users

### Support Tools
- `/report` - Report a bug or issue with a bot
- `/support` - Get information on how to contact staff for help
- `/faq` - View answers to common questions and concerns

### Administrative Commands
- `/update-status` - Update the status of an order (staff only)
- `/approve-payment` - Approve a payment for an order (staff only)
- `/reject-payment` - Reject a payment for an order with reason (staff only)
- `/add-tip` - Add a new daily tip (staff only)
- `/view-feedback` - View all pending feedback (staff only)

## Installation

### Requirements
- Python 3.8 or higher
- PostgreSQL database
- Discord API token

### Setup
1. Clone the repository:
   ```
   git clone https://github.com/joelikes8/HUBBOT-DC.git
   cd HUBBOT-DC
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables (in a `.env` file):
   ```
   DISCORD_TOKEN=your_discord_token
   DATABASE_URL=postgresql://user:password@host:port/database
   ```

4. Run the bot:
   ```
   python bot_runner.py
   ```

## Database Structure

The bot uses PostgreSQL for data storage with the following tables:
- Users - Store Discord users and their linked Roblox usernames
- Orders - Track bot orders and their statuses
- Payments - Store payment proofs and approval status
- Giveaways - Manage ongoing and completed giveaways
- Daily Tips - Store helpful tips for users
- Feedback - Track user suggestions and issues

## License

This project is proprietary software.
