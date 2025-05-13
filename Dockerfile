FROM python:3.12-slim

WORKDIR /app

# Install only the required packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY mayer_monitor.py .

# Set the entrypoint to run the script
ENTRYPOINT ["python", "mayer_monitor.py"] 