# GitHub Events Pipeline

A minimal real-time data pipeline that processes GitHub events through Kafka and Spark, storing them in Iceberg tables with a web dashboard.

## Architecture

```
GitHub API → Producer → Kafka → Spark Streaming → Iceberg → API → Dashboard
```

## Quick Start

**Prerequisites:** Docker & Docker Compose

**One command setup:**
```bash
export GITHUB_TOKEN=your_token_here && ./setup.sh
```

That's it! The pipeline will start automatically.

**Performance Note:** Docker images use `uv` for ultra-fast Python package installation, significantly reducing build times.

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| 📊 **Dashboard** | http://localhost:8080 | Real-time monitoring |
| 📤 **Producer API** | http://localhost:8001 | Control producer |
| ⚡ **Streaming API** | http://localhost:8002 | Control streaming |
| 🔍 **Query API** | http://localhost:8003 | Data access |
| 📋 **Kafka UI** | http://localhost:8081 | Kafka topics & messages |


## Manual Control

Start the pipeline manually:
```bash
# Start producer
curl -X POST http://localhost:8001/start

# Start streaming
curl -X POST http://localhost:8002/start
```

## Management

```bash
# View logs
docker-compose logs -f [service-name]

# Stop all
docker-compose down

# Restart service
docker-compose restart [service-name]
```

## Project Structure

```
├── services/
│   ├── producer-service/     # GitHub events producer
│   ├── streaming-service/    # Spark streaming processor
│   ├── api-service/         # REST API for data access
│   └── dashboard-service/   # Web dashboard
├── docker-compose.yml       # All services
└── setup.sh                # One-command setup
```

Each service is self-contained with its own configuration and deployment files.

## Configuration

Set environment variables before running:

```bash
# Optional: Set GitHub token for higher rate limits
export GITHUB_TOKEN=your_github_token

# Or create a .env file in the project root:
echo "GITHUB_TOKEN=your_github_token" > .env
```

**Note:** The `.env` file is gitignored for security. Create it locally with your GitHub token.

## Data Flow

1. **Producer** fetches GitHub events from public API
2. **Kafka** streams events in real-time
3. **Spark Streaming** processes and enriches events
4. **Iceberg** stores data with ACID transactions (local filesystem)
5. **API** provides REST endpoints for querying
6. **Dashboard** visualizes real-time metrics

## Troubleshooting

**No data in dashboard:**
- Check producer: `docker-compose logs producer-service`
- Check streaming: `docker-compose logs streaming-service`
- Verify Kafka topic: `docker exec kafka kafka-topics --list --bootstrap-server localhost:9092`

**Long startup due to jar downloads:**
- The stack uses only two small Maven packages now (Iceberg runtime, Spark Kafka). A local Ivy cache is persisted to avoid re-downloading on restarts.

**Services won't start:**
- Check Docker resources: `docker system df`
- Clean up: `docker system prune -f`
- Restart: `docker-compose down && ./setup.sh`
