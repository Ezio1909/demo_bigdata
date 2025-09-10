FROM bitnami/spark:3.4.1

# Switch to root to install dependencies
USER root

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Create application directory
WORKDIR /app

# Copy application code
COPY . .

# Create iceberg directory
RUN mkdir -p /opt/iceberg/warehouse /opt/iceberg/checkpoints && \
    chown -R 1001:1001 /opt/iceberg /app

# Switch back to spark user
USER 1001

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=60s --retries=3 \
    CMD python -c "import pyspark; print('Spark OK')" || exit 1

# Run the streaming API
CMD ["python", "streaming_api.py"]
