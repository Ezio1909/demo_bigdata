FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/producer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/producer/ .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://api.github.com', timeout=5)" || exit 1

# Run the producer API
ENV PYTHONPATH=/app:/common
CMD ["python", "api.py"]
