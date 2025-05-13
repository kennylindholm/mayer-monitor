import requests
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler, JobQueue
import logging
import sqlite3
from contextlib import contextmanager
import pytz

# Load environment variables
load_dotenv()

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Configure logging based on DEBUG environment variable
log_level = logging.DEBUG if os.getenv('DEBUG', '').lower() in ('true', '1', 't') else logging.INFO
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=log_level,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Database setup
DB_PATH = os.getenv('DB_PATH', 'mayer_monitor.db')

# Timezone setup
SWEDISH_TZ = pytz.timezone('Europe/Stockholm')

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database with required tables"""
    with get_db_connection() as conn:
        db = conn.cursor()
        db.execute('''
            CREATE TABLE IF NOT EXISTS mayer_values (
                timestamp DATETIME PRIMARY KEY,
                mayer_multiple REAL,
                price REAL,
                ma_200 REAL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                chat_id INTEGER PRIMARY KEY,
                enabled BOOLEAN,
                last_notified DATETIME
            )
        ''')
        conn.commit()
        logger.info("Database initialized successfully")

def store_mayer_value(timestamp, mayer_multiple, price, ma_200):
    """Store a new Mayer Multiple value in the database"""
    with get_db_connection() as conn:
        db = conn.cursor()
        db.execute('''
            INSERT INTO mayer_values (timestamp, mayer_multiple, price, ma_200)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, mayer_multiple, price, ma_200))
        conn.commit()
        logger.debug(f"Stored Mayer Multiple value: {mayer_multiple:.2f}")

def get_recent_mayer_values(days=7):
    """Get Mayer Multiple values for the last N days"""
    with get_db_connection() as conn:
        db = conn.cursor()
        db.execute('''
            SELECT mayer_multiple, timestamp
            FROM mayer_values
            WHERE timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
        ''', (f'-{days} days',))
        return db.fetchall()

def get_notification_chats():
    """Get all chat IDs that have notifications enabled"""
    with get_db_connection() as conn:
        db = conn.cursor()
        db.execute('SELECT chat_id FROM notifications WHERE enabled = 1')
        return {row[0] for row in db.fetchall()}

def check_sell_condition():
    """
    Check if Mayer Multiple has been above 2.4 for 7 consecutive days
    """
    recent_values = get_recent_mayer_values(7)
    if len(recent_values) < 7:
        return False
    
    return all(value[0] > 2.4 for value in recent_values)

def get_bitcoin_price():
    """
    Get current Bitcoin price from CoinGecko
    """
    logger.debug("Fetching current Bitcoin price from CoinGecko")
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        price = float(data['bitcoin']['usd'])
        logger.debug(f"Successfully fetched Bitcoin price: ${price:,.2f}")
        return price
    except Exception as e:
        logger.error(f"Error fetching Bitcoin price: {e}", exc_info=True)
        return None

def get_200_day_ma():
    """
    Get 200-day moving average from CoinGecko
    """
    logger.debug("Calculating 200-day moving average")
    # Get historical data for the last 200 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=200)
    
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range"
    params = {
        'vs_currency': 'usd',
        'from': int(start_date.timestamp()),
        'to': int(end_date.timestamp())
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Calculate 200-day moving average
        prices = [price[1] for price in data['prices']]
        if len(prices) >= 200:
            ma_200 = sum(prices[-200:]) / 200
            logger.debug(f"Successfully calculated 200-day MA: ${ma_200:,.2f}")
            return ma_200
        else:
            logger.warning(f"Not enough historical data for 200-day MA. Got {len(prices)} days of data")
            return None
            
    except Exception as e:
        logger.error(f"Error calculating 200-day MA: {e}", exc_info=True)
        return None

def get_mayer_multiple():
    """
    Calculate the Mayer Multiple (current price / 200-day moving average)
    """
    logger.debug("Calculating Mayer Multiple")
    current_price = get_bitcoin_price()
    ma_200 = get_200_day_ma()
    
    if current_price is None or ma_200 is None:
        logger.error("Failed to calculate Mayer Multiple due to missing price data")
        return None, None, None
        
    mayer_multiple = current_price / ma_200
    logger.info(f"Mayer Multiple: {mayer_multiple:.2f} (Price: ${current_price:,.2f}, MA: ${ma_200:,.2f})")
    
    # Store the value in the database
    store_mayer_value(datetime.now(), mayer_multiple, current_price, ma_200)
    
    return mayer_multiple, current_price, ma_200

def analyze_mayer_multiple(value):
    """
    Analyze the Mayer Multiple and provide trading signals
    """
    if value is None:
        logger.error("Cannot analyze Mayer Multiple: value is None")
        return "ERROR: Could not calculate Mayer Multiple", None
    
    if value < 1.0:
        logger.info(f"BUY signal: Mayer Multiple {value:.2f} < 1.0")
        return "🚀 BUY SIGNAL: Mayer Multiple is below 1.0", "BUY"
    elif value > 2.4:
        if check_sell_condition():
            logger.info(f"SELL signal: Mayer Multiple {value:.2f} > 2.4 for 7 consecutive days")
            return "📉 SELL SIGNAL: Mayer Multiple has been above 2.4 for 7 consecutive days", "SELL"
        else:
            recent_values = get_recent_mayer_values(7)
            days_above = sum(1 for v, _ in recent_values if v > 2.4)
            logger.info(f"Watching: Mayer Multiple {value:.2f} > 2.4 ({days_above}/7 days)")
            return f"👀 WATCHING: Mayer Multiple is above 2.4 ({days_above}/7 days)", "WATCHING"
    else:
        logger.info(f"HOLD signal: Mayer Multiple {value:.2f}")
        return f"⏳ HOLD: Mayer Multiple is {value:.2f}", "HOLD"

def format_message(current_time, mayer_value, current_price, ma_200, signal):
    """
    Format the message for Telegram
    """
    logger.debug("Formatting Telegram message")
    return f"""
<b>Mayer Multiple Update</b>
Time: {current_time}

💰 Current BTC Price: ${current_price:,.2f}
📊 200-day MA: ${ma_200:,.2f}
📈 Mayer Multiple: {mayer_value:.2f}

{signal}
"""

def check_mayer_multiple(context):
    """
    Periodic check of Mayer Multiple and send notifications if needed
    """
    logger.info("Running periodic Mayer Multiple check")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mayer_value, current_price, ma_200 = get_mayer_multiple()
    
    if mayer_value is not None:
        signal_text, signal_type = analyze_mayer_multiple(mayer_value)
        
        # Send notifications for BUY signals and confirmed SELL signals
        if signal_type in ["BUY", "SELL"]:
            message = format_message(current_time, mayer_value, current_price, ma_200, signal_text)
            notification_chats = get_notification_chats()
            for chat_id in notification_chats:
                try:
                    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                    logger.info(f"Sent {signal_type} notification to chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification to chat {chat_id}: {e}")

def status(update, context):
    """
    Handle /status command
    """
    user = update.effective_user
    logger.info(f"Status request from {user.username or user.id}")
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mayer_value, current_price, ma_200 = get_mayer_multiple()
    
    if mayer_value is not None:
        signal_text, _ = analyze_mayer_multiple(mayer_value)
        message = format_message(current_time, mayer_value, current_price, ma_200, signal_text)
        update.message.reply_text(message, parse_mode='HTML')
        logger.debug(f"Status update sent to {user.username or user.id}")
    else:
        error_msg = "❌ Failed to calculate Mayer Multiple"
        update.message.reply_text(error_msg)
        logger.error(f"Failed to send status update to {user.username or user.id}")

def toggle_notifications(update, context):
    """
    Handle /notify command to toggle notifications
    """
    chat_id = update.effective_chat.id
    with get_db_connection() as conn:
        db = conn.cursor()
        # Get current state
        db.execute('SELECT enabled FROM notifications WHERE chat_id = ?', (chat_id,))
        result = db.fetchone()
        # Enable notifications by default if user is new
        if result is None:
            current_state = False
            new_state = True
        else:
            current_state = result[0]
            new_state = not current_state
        db.execute('''
            INSERT OR REPLACE INTO notifications (chat_id, enabled, last_notified)
            VALUES (?, ?, datetime('now'))
        ''', (chat_id, new_state))
        conn.commit()
        
        if new_state:
            update.message.reply_text("✅ Notifications enabled - you will receive alerts for BUY/SELL signals")
            logger.info(f"Notifications enabled for chat {chat_id}")
        else:
            update.message.reply_text("❌ Notifications disabled")
            logger.info(f"Notifications disabled for chat {chat_id}")

def help_command(update, context):
    """
    Handle /help command
    """
    user = update.effective_user
    logger.info(f"Help request from {user.username or user.id}")
    
    help_text = (
        "<b>Available Commands:</b>\n\n"
        "/status - Get current Mayer Multiple status\n"
        "/notify - Toggle BUY/SELL signal notifications\n"
        "/help - Show this help message\n\n"
        "<b>Mayer Multiple Rules:</b>\n"
        "🚀 BUY when Mayer Multiple &lt; 1.0\n"
        "📉 SELL when Mayer Multiple &gt; 2.4 for 7 consecutive days\n"
        "⏳ HOLD otherwise"
    )
    
    try:
        update.message.reply_text(help_text, parse_mode='HTML')
        logger.debug(f"Help message sent to {user.username or user.id}")
    except Exception as e:
        logger.error(f"Failed to send help message: {e}")
        # Fallback to plain text if HTML fails
        plain_text = (
            "Available Commands:\n\n"
            "/status - Get current Mayer Multiple status\n"
            "/notify - Toggle BUY/SELL signal notifications\n"
            "/help - Show this help message\n\n"
            "Mayer Multiple Rules:\n"
            "🚀 BUY when Mayer Multiple < 1.0\n"
            "📉 SELL when Mayer Multiple > 2.4 for 7 consecutive days\n"
            "⏳ HOLD otherwise"
        )
        update.message.reply_text(plain_text)

def get_swedish_time():
    """Get current time in Swedish timezone"""
    return datetime.now(SWEDISH_TZ)

def main():
    """
    Main function to run the bot
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment variables")
        return

    logger.info("Starting Mayer Multiple Monitor Bot")
    
    # Initialize database
    init_db()
    
    # Create the Updater
    updater = Updater(TELEGRAM_BOT_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add command handlers
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("notify", toggle_notifications))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("start", help_command))

    # Enable notifications by default for new users on /start
    def enable_notify_on_start(update, context):
        chat_id = update.effective_chat.id
        with get_db_connection() as conn:
            db = conn.cursor()
            db.execute('SELECT enabled FROM notifications WHERE chat_id = ?', (chat_id,))
            result = db.fetchone()
            if result is None:
                db.execute('''
                    INSERT INTO notifications (chat_id, enabled, last_notified)
                    VALUES (?, 1, datetime('now'))
                ''', (chat_id,))
                conn.commit()
                logger.info(f"Notifications enabled by default for new chat {chat_id}")
        help_command(update, context)
    
    dispatcher.add_handler(CommandHandler("start", enable_notify_on_start))

    # Add daily job to check Mayer Multiple at 06:00 Swedish time
    job_queue = updater.job_queue
    swedish_time = datetime.strptime("06:00", "%H:%M").time()
    job_queue.run_daily(
        check_mayer_multiple,
        time=swedish_time,
        days=(0, 1, 2, 3, 4, 5, 6)  # Run every day
    )
    logger.info(f"Scheduled daily Mayer Multiple check for 06:00 {SWEDISH_TZ.zone}")

    # Start the Bot
    updater.start_polling()
    logger.info("Bot started successfully")

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == "__main__":
    main() 