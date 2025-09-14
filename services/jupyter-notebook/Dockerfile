FROM python:3.9-slim-bullseye

WORKDIR /workspace

# System deps: Java for Spark + basics
RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Faster Python installs
RUN pip install uv

# Python deps
COPY services/jupyter-notebook/requirements.txt /tmp/requirements.txt
RUN uv pip install --system --no-cache -r /tmp/requirements.txt

# Create ivy cache dir for Spark packages
RUN mkdir -p /opt/ivy

# Expose Jupyter port
EXPOSE 8888

# Default command runs Jupyter Lab with no token (local dev only)
# Use ServerApp.* flags and allow root inside container
CMD ["bash", "-lc", "jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --ServerApp.token='' --ServerApp.password='' --ServerApp.allow_origin='*' --ServerApp.base_url='/'"]

