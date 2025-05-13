# Mayer Multiple Monitor

This application monitors the Mayer Multiple from charts.bitbo.io and provides trading signals based on the following rules:
- BUY when Mayer Multiple is less than 1.0
- SELL when Mayer Multiple is above 2.4 for more than 7 days

## Requirements
- Podman

## Running the Application

1. Build the container image:
```bash
podman build -t mayer-monitor .
```

2. Run the container:
```bash
podman run mayer-monitor
```

The application will check the Mayer Multiple every hour and print the current status and any trading signals.

## Current Features
- Fetches Mayer Multiple from charts.bitbo.io
- Provides basic BUY/SELL signals based on the Mayer Multiple value
- Runs in a container
- Checks every hour

## Future Improvements
- Add notification system (email, SMS, etc.)
- Implement 7-day tracking for SELL signals
- Add historical data tracking
- Add configuration options for thresholds 