import requests
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler
import logging

# Load environment variables
load_dotenv()

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_bitcoin_price():
    """
    Get current Bitcoin price from CoinGecko
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return float(data['bitcoin']['usd'])
    except Exception as e:
        print(f"Error fetching Bitcoin price: {e}")
        return None

def get_200_day_ma():
    """
    Get 200-day moving average from CoinGecko
    """
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
            return sum(prices[-200:]) / 200
        else:
            print("Not enough historical data for 200-day MA")
            return None
            
    except Exception as e:
        print(f"Error fetching 200-day MA: {e}")
        return None

def get_mayer_multiple():
    """
    Calculate the Mayer Multiple (current price / 200-day moving average)
    """
    current_price = get_bitcoin_price()
    ma_200 = get_200_day_ma()
    
    if current_price is None or ma_200 is None:
        return None, None, None
        
    mayer_multiple = current_price / ma_200
    return mayer_multiple, current_price, ma_200

def analyze_mayer_multiple(value):
    """
    Analyze the Mayer Multiple and provide trading signals
    """
    if value is None:
        return "ERROR: Could not calculate Mayer Multiple"
    
    if value < 1.0:
        return "🚀 BUY SIGNAL: Mayer Multiple is below 1.0"
    elif value > 2.4:
        return "📉 SELL SIGNAL: Mayer Multiple is above 2.4"
    else:
        return f"⏳ HOLD: Mayer Multiple is {value:.2f}"

def format_message(current_time, mayer_value, current_price, ma_200, signal):
    """
    Format the message for Telegram
    """
    return f"""
<b>Mayer Multiple Update</b>
Time: {current_time}

💰 Current BTC Price: ${current_price:,.2f}
📊 200-day MA: ${ma_200:,.2f}
📈 Mayer Multiple: {mayer_value:.2f}

{signal}
"""

def status(update, context):
    """
    Handle /status command
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mayer_value, current_price, ma_200 = get_mayer_multiple()
    
    if mayer_value is not None:
        signal = analyze_mayer_multiple(mayer_value)
        message = format_message(current_time, mayer_value, current_price, ma_200, signal)
        update.message.reply_text(message, parse_mode='HTML')
    else:
        update.message.reply_text("❌ Failed to calculate Mayer Multiple")

def help_command(update, context):
    """
    Handle /help command
    """
    help_text = """
<b>Available Commands:</b>

/status - Get current Mayer Multiple status
/help - Show this help message

<b>Mayer Multiple Rules:</b>
🚀 BUY when Mayer Multiple < 1.0
📉 SELL when Mayer Multiple > 2.4
⏳ HOLD otherwise
"""
    update.message.reply_text(help_text, parse_mode='HTML')

def main():
    """
    Main function to run the bot
    """
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        return

    # Create the Updater
    updater = Updater(TELEGRAM_BOT_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add command handlers
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("start", help_command))

    # Start the Bot
    updater.start_polling()
    print("Bot started. Press Ctrl+C to stop.")

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == "__main__":
    main() 