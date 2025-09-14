FROM python:3.9-slim-bullseye

WORKDIR /app

# Install system dependencies (Java for Spark, curl for healthchecks)
RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    gcc \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package installation
RUN pip install uv

# Copy requirements and install Python dependencies with uv
COPY services/streaming-service/requirements.txt /tmp/requirements.txt
RUN uv pip install --system --no-cache -r /tmp/requirements.txt

# Copy application code
COPY services/streaming-service/ .

# Create iceberg directories
RUN mkdir -p /opt/iceberg/warehouse /opt/iceberg/checkpoints

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=60s --retries=3 \
    CMD python -c "import pyspark; print('Spark OK')" || exit 1

# Run the streaming API
ENV PYTHONPATH=/app:/common
CMD ["python", "api.py"]
