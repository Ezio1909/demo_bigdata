# Real-time GitHub Event Processing System

A complete data pipeline that consumes GitHub events in real-time, processes them through Kafka and Spark, stores them in Iceberg tables, and provides a real-time monitoring dashboard.

## 🏗️ Architecture Overview

```
GitHub API → Python Producer → Kafka → Spark Streaming → Iceberg Table → REST API → Web Dashboard
```

The system consists of several interconnected components:

- **Data Ingestion**: Python service fetches events from GitHub's public events API
- **Message Streaming**: Kafka handles real-time event streaming with automatic cleanup
- **Stream Processing**: Spark Streaming processes events and writes to Iceberg tables
- **Data Storage**: Apache Iceberg tables stored in MinIO (S3-compatible storage)
- **API Layer**: FastAPI service provides REST endpoints for data access
- **Visualization**: Real-time web dashboard with charts and event monitoring
- **Data Lifecycle**: Automatic cleanup of data older than 1 hour

## Requirements and One-Line Start

- Docker & Docker Compose
- 8GB+ RAM recommended
- 10GB+ free disk space

Start everything and begin the data flow (producer + streaming):

```bash
export GITHUB_TOKEN=your_token_here && cd /Users/nampham/demo_bigdata && ./scripts/setup-microservices.sh && curl -sS -X POST http://localhost:8001/start && curl -sS -X POST http://localhost:8002/start
```

### Logs & Debugging (quick references)

```bash
# All services (tail)
docker-compose -f docker-compose-microservices.yml logs -f --tail=100

# Producer / Streaming / Query API
docker-compose -f docker-compose-microservices.yml logs -f --tail=200 github-producer-service
docker-compose -f docker-compose-microservices.yml logs -f --tail=200 spark-streaming-service
docker-compose -f docker-compose-microservices.yml logs -f --tail=200 data-query-service

# Dashboard / Registry / Infra
docker-compose -f docker-compose-microservices.yml logs -f dashboard-service service-registry kafka zookeeper minio kafka-ui

# Health checks
curl -s http://localhost:8001/health; echo
curl -s http://localhost:8002/health; echo
curl -s http://localhost:8003/health; echo

# Exec into a container
docker exec -it spark-streaming-service bash
```

Note: If you’re behind a corporate proxy and the producer shows SSL errors to `api.github.com`, install your org CA in the producer container or set `REQUESTS_CA_BUNDLE` to a CA bundle that includes it.

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 8GB+ RAM recommended
- 10GB+ free disk space

### One-Command Setup

```bash
./scripts/setup.sh
```

This script will:
- Check Docker installation
- Build all required images
- Start infrastructure services (Kafka, Spark, MinIO)
- Create necessary topics and storage
- Launch all application services
- Display service URLs and credentials

### Manual Setup

If you prefer manual setup:

```bash
# 1. Start infrastructure
docker-compose up -d zookeeper kafka minio spark-master spark-worker

# 2. Create Kafka topic
./kafka/create-topic.sh

# 3. Start application services
docker-compose up -d github-producer spark-consumer api dashboard
```

## 📊 Service URLs

Once running, access these services:

| Service | URL | Description |
|---------|-----|-------------|
| 📊 **Dashboard** | http://localhost:8080 | Real-time monitoring interface |
| 🔌 **REST API** | http://localhost:8000 | Data access API |
| 📚 **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| ⚡ **Kafka UI** | http://localhost:8090 | Kafka cluster monitoring |
| 🗄️ **MinIO Console** | http://localhost:9001 | Object storage management |
| ⚙️ **Spark UI** | http://localhost:8080 | Spark cluster monitoring |

**Default Credentials:**
- MinIO: `minioadmin` / `minioadmin123`

## 🛠️ Components

### 1. GitHub Event Producer (`producer/`)
- Fetches events from GitHub's public events API
- Implements rate limiting and error handling
- Publishes events to Kafka with proper serialization
- Supports GitHub token for higher rate limits

### 2. Kafka Infrastructure
- High-throughput message streaming
- Automatic data retention (2 hours max)
- Partitioned topics for scalability
- Web UI for monitoring

### 3. Spark Streaming Consumer (`spark/`)
- Real-time stream processing
- Transforms and enriches event data
- Writes to Iceberg tables with automatic partitioning
- Handles schema evolution and data quality

### 4. Apache Iceberg Storage
- ACID transactions and schema evolution
- Time-travel capabilities
- Efficient data organization with partitioning
- S3-compatible storage backend (MinIO)

### 5. REST API (`api/`)
- FastAPI with automatic documentation
- Comprehensive event querying and filtering
- Real-time statistics and aggregations
- Health checks and monitoring endpoints

### 6. Web Dashboard (`dashboard/`)
- Real-time event visualization
- Interactive charts and metrics
- Event filtering and search
- Export functionality for data and charts

### 7. Data Cleanup
- Automatic deletion of data older than 1 hour
- Configurable retention policies
- Prevents storage overflow

## 🔧 Configuration

### GitHub Token (Recommended)

To avoid rate limiting, add your GitHub personal access token:

1. Create a token at https://github.com/settings/tokens
2. Add to `producer/.env`:
   ```
   GITHUB_TOKEN=your_token_here
   ```
3. Restart the producer: `docker-compose restart github-producer`

### Environment Variables

Key configuration files:
- `producer/.env` - GitHub API and Kafka settings
- `api/.env` - API and storage configuration  
- `spark/.env` - Spark and streaming settings

### Scaling Configuration

To handle higher loads:

```yaml
# In docker-compose.yml, increase resources:
spark-worker:
  environment:
    - SPARK_WORKER_MEMORY=4G
    - SPARK_WORKER_CORES=4
  deploy:
    replicas: 2
```

## 📈 Monitoring & Operations

### View Logs

```bash
# All services
./scripts/logs.sh

# Specific service
./scripts/logs.sh github-producer

# Last 100 lines
./scripts/logs.sh api --tail 100
```

### Service Management

```bash
# Check status
docker-compose ps

# Restart service
docker-compose restart [service-name]

# Scale service
docker-compose up -d --scale spark-worker=2
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Service stats
curl http://localhost:8000/stats
```

## 🔍 Data Schema

### GitHub Event Structure

Events are stored with the following schema:

```sql
CREATE TABLE github_events.events (
    event_id STRING,
    event_type STRING,
    event_category STRING,
    created_at TIMESTAMP,
    processed_at TIMESTAMP,
    actor_id INT,
    actor_login STRING,
    repo_id INT,
    repo_name STRING,
    org_id INT,
    org_login STRING,
    action STRING,
    payload_json STRING,
    processing_date STRING,
    processing_hour INT
) PARTITIONED BY (processing_date, processing_hour)
```

### Event Categories

Events are categorized for easier analysis:
- **code**: Push, Pull Request, Commit Comment events
- **issues**: Issues, Issue Comment events  
- **social**: Watch, Fork events
- **repository**: Create, Delete, Public events
- **releases**: Release events
- **collaboration**: Member, Team events

## 🚨 Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check Docker resources
docker system df
docker system prune -f

# Restart with clean state
./scripts/stop.sh --volumes
./scripts/setup.sh
```

**No data in dashboard:**
- Check if GitHub producer is running: `docker logs github-events-producer`
- Verify Kafka topic exists: `docker exec github-events-kafka kafka-topics --list --bootstrap-server localhost:9092`
- Check Spark consumer logs: `docker logs github-events-spark-consumer`

**API errors:**
- Ensure Spark master is running: `curl http://localhost:8080`
- Check MinIO accessibility: `curl http://localhost:9000/minio/health/live`
- Verify Iceberg table exists in MinIO console

**High memory usage:**
- Reduce Spark worker memory in docker-compose.yml
- Decrease retention periods in Kafka configuration
- Monitor with `docker stats`

### Performance Tuning

**For higher throughput:**
1. Increase Kafka partitions
2. Add more Spark workers
3. Tune batch sizes in Spark streaming
4. Use SSD storage for better I/O

**For lower resource usage:**
1. Reduce fetch intervals
2. Decrease worker memory allocation
3. Enable compression in Kafka
4. Optimize Iceberg file sizes

## 🛑 Shutdown

```bash
# Stop all services
./scripts/stop.sh

# Stop and remove all data
./scripts/stop.sh --volumes
```

## 🔐 Security Notes

This is a development setup. For production:

- Enable authentication for all services
- Use proper TLS certificates
- Implement network segmentation
- Set up proper monitoring and alerting
- Use secrets management for credentials
- Enable audit logging

## 📚 API Reference

### Endpoints

- `GET /health` - Service health check
- `GET /events` - List events with filtering
- `GET /stats` - Dashboard statistics
- `GET /event-types` - Available event types
- `GET /event-categories` - Available categories

### Example API Calls

```bash
# Get recent events
curl "http://localhost:8000/events?hours_back=1&page_size=10"

# Filter by event type
curl "http://localhost:8000/events?event_type=PushEvent"

# Get statistics
curl "http://localhost:8000/stats?hours_back=6"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `./scripts/setup.sh`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- GitHub API for providing public event data
- Apache Kafka, Spark, and Iceberg communities
- Docker and container ecosystem
- Chart.js for visualization components
# demo_bigdata
