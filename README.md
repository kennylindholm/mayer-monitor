# Mayer Multiple Monitor

This application monitors the Mayer Multiple from CoinGecko and provides trading signals based on the following rules:
- BUY when Mayer Multiple is less than 1.0
- SELL when Mayer Multiple is above 2.4 for more than 7 days

## Requirements
- Docker

## Running the Application

1. Build the container image:
```bash
docker build -t mayer-monitor .
```

2. Run the container:
```bash
docker run --env-file .env mayer-monitor
```

The application will check the Mayer Multiple daily at 06:00 Swedish time and send notifications for BUY/SELL signals to users who have enabled them.

## Current Features
- Fetches Mayer Multiple from CoinGecko
- Provides basic BUY/SELL signals based on the Mayer Multiple value
- Runs in a container
- Checks daily at 06:00 Swedish time
- Sends notifications for BUY/SELL signals to users who have enabled them
- Supports Telegram bot commands for status updates and notification toggling

## Future Improvements
- Add notification system (email, SMS, etc.)
- Implement 7-day tracking for SELL signals
- Add historical data tracking
- Add configuration options for thresholds
- Enhance test coverage and add integration tests 