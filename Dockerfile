FROM python:3.11-slim

LABEL org.opencontainers.image.authors="danielgoepp"
LABEL org.opencontainers.image.source="https://github.com/danielgoepp/m2m"

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mitsubishi_mqtt_processor.py config.py .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Run the application
CMD ["python", "mitsubishi_mqtt_processor.py"]