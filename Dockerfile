FROM python:3.12-slim

WORKDIR /app
ENV SERVICE_ACCOUNT=python

# Install only the required packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    adduser --system \
    --shell /bin/false \
    --disabled-password \
    --uid 1001 $SERVICE_ACCOUNT \
    --home /home/python

# Copy the script
COPY mayer_monitor.py .


# Set the user to a non-root user
USER $SERVICE_ACCOUNT
# Set the entrypoint to run the script
ENTRYPOINT ["python", "mayer_monitor.py"] 
