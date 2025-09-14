FROM python:3.9-slim-bullseye

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    gcc \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Note: JAVA_HOME is not strictly required as long as 'java' is on PATH.
# If needed, set it explicitly per-arch, e.g. for amd64: /usr/lib/jvm/java-17-openjdk-amd64

# Install uv for faster Python package installation
RUN pip install uv

# Copy requirements and install Python dependencies with uv
COPY services/api-service/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code
COPY services/api-service/ .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

ENV PYTHONPATH=/app:/common
# Run the API server
CMD ["python", "app.py"]
