FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package installation
RUN pip install uv

# Copy requirements and install Python dependencies with uv
COPY services/producer-service/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code
COPY services/producer-service/ .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://api.github.com', timeout=5)" || exit 1

# Run the producer API
ENV PYTHONPATH=/app:/common
CMD ["python", "api.py"]
