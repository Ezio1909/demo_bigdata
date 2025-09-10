# 🐳 GitHub Events Microservices Architecture

A **containerized microservices architecture** where each component is isolated, communicates via APIs, and can be managed independently.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub API    │    │   Kafka Topic   │    │  Iceberg Table  │
│                 │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Producer Service│    │Streaming Service│    │  Query Service  │
│   (Port 8001)   │    │   (Port 8002)   │    │   (Port 8003)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────────┐
                    │Service Registry │
                    │   (Port 8000)   │
                    └─────────────────┘
```

## 🚀 Quick Start

```bash
# One command setup
./scripts/setup-microservices.sh && curl -sS -X POST http://localhost:8001/start && curl -sS -X POST http://localhost:8002/start
```

## 📊 Service Endpoints

| Service | Port | Purpose | API Docs |
|---------|------|---------|----------|
| 🌐 **Dashboard** | 8080 | Web interface | - |
| 📋 **Service Registry** | 8000 | Health monitoring | http://localhost:8000/docs |
| 📤 **Producer Service** | 8001 | GitHub → Kafka | http://localhost:8001/docs |
| ⚡ **Streaming Service** | 8002 | Kafka → Iceberg | http://localhost:8002/docs |
| 🔍 **Query Service** | 8003 | Iceberg → API | http://localhost:8003/docs |
| ⚡ **Kafka UI** | 8090 | Kafka monitoring | - |
| 🗄️ **MinIO Console** | 9001 | Storage management | - |

## 🎮 How to Control the Pipeline

### 1. Start the Data Pipeline

```bash
# Start GitHub events producer
curl -X POST http://localhost:8001/start

# Start Spark streaming (Kafka → Iceberg)
curl -X POST http://localhost:8002/start
```

### 2. Monitor Services

```bash
# Check all services health
curl http://localhost:8000/services

# Check producer status
curl http://localhost:8001/status

# Check streaming status
curl http://localhost:8002/status

# Get table statistics
curl http://localhost:8002/table/info
```

### 3. Query Data

```bash
# Get recent events
curl "http://localhost:8003/events?hours_back=1&page_size=10"

# Get dashboard statistics
curl "http://localhost:8003/stats?hours_back=6"

# Filter by event type
curl "http://localhost:8003/events?event_type=PushEvent"
```

### 4. Stop Services

```bash
# Stop producer
curl -X POST http://localhost:8001/stop

# Stop streaming
curl -X POST http://localhost:8002/stop
```

## 🔧 Service Configuration

### Producer Service API

```bash
# Update producer configuration
curl -X POST http://localhost:8001/config \
  -H "Content-Type: application/json" \
  -d '{
    "fetch_interval_seconds": 15,
    "max_events_per_fetch": 200,
    "github_token": "your_token_here"
  }'

# Get producer statistics
curl http://localhost:8001/stats
```

### Streaming Service API

```bash
# Update streaming configuration
curl -X POST http://localhost:8002/config \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_interval": "15 seconds",
    "max_events_per_batch": 2000
  }'

# Get streaming statistics
curl http://localhost:8002/stats
```

## 🏗️ Microservices Benefits

### ✅ **Isolation & Independence**
- Each service runs in its own container
- Services can be started/stopped independently
- Failures in one service don't affect others
- Easy to scale individual components

### ✅ **API-First Design**
- All services expose REST APIs
- Easy to integrate with external tools
- Standard HTTP communication
- Built-in API documentation

### ✅ **Observability**
- Centralized service registry
- Health checks for all services
- Detailed metrics and statistics
- Easy debugging and monitoring

### ✅ **Development Friendly**
- No machine pollution (everything containerized)
- Easy to modify individual services
- Hot reloading during development
- Clear separation of concerns

## 🔍 Service Details

### 📤 Producer Service (Port 8001)
- **Purpose**: Fetches GitHub events and publishes to Kafka
- **API**: REST endpoints for start/stop/configure
- **Features**: Rate limiting, error handling, statistics
- **Health**: `/health`, `/status`, `/stats`

### ⚡ Streaming Service (Port 8002)
- **Purpose**: Processes Kafka events and writes to Iceberg
- **API**: REST endpoints for stream control
- **Features**: Real-time processing, data quality checks
- **Health**: `/health`, `/status`, `/table/info`

### 🔍 Query Service (Port 8003)
- **Purpose**: Queries Iceberg data via REST API
- **API**: Event filtering, statistics, pagination
- **Features**: Fast queries, caching, filtering
- **Health**: `/health`, `/events`, `/stats`

### 📋 Service Registry (Port 8000)
- **Purpose**: Centralized health monitoring
- **API**: Service discovery and health checks
- **Features**: Automatic health monitoring, service status
- **Health**: `/services`, `/health`

## 🛠️ Development Workflow

### 1. **Modify a Service**
```bash
# Edit service code
vim producer/producer_api.py

# Rebuild and restart
docker-compose -f docker-compose-microservices.yml build github-producer-service
docker-compose -f docker-compose-microservices.yml restart github-producer-service
```

### 2. **Debug a Service**
```bash
# View logs
docker-compose -f docker-compose-microservices.yml logs -f github-producer-service

# Execute into container
docker exec -it github-producer-service bash

# Check service health
curl http://localhost:8001/health
```

### 3. **Scale Services**
```bash
# Scale streaming service
docker-compose -f docker-compose-microservices.yml up -d --scale spark-streaming-service=2
```

## 📊 Monitoring & Operations

### Service Health Dashboard
Visit http://localhost:8000/services to see:
- Service status (healthy/unhealthy)
- Response times
- Last check times
- Error messages

### Individual Service Monitoring
Each service provides detailed metrics:
- **Producer**: Events fetched, sent, errors, rate limits
- **Streaming**: Events processed, batches, table info
- **Query**: Query performance, cache hits
- **Registry**: Service discovery, health checks

### Log Aggregation
```bash
# View all logs
docker-compose -f docker-compose-microservices.yml logs

# View specific service logs
docker-compose -f docker-compose-microservices.yml logs -f github-producer-service

# Follow logs in real-time
docker-compose -f docker-compose-microservices.yml logs -f --tail=100
```

## 🚨 Troubleshooting

### Service Won't Start
```bash
# Check service logs
docker-compose -f docker-compose-microservices.yml logs [service-name]

# Check service health
curl http://localhost:8000/services

# Restart service
docker-compose -f docker-compose-microservices.yml restart [service-name]
```

### No Data Flow
```bash
# Check if producer is running
curl http://localhost:8001/status

# Check if streaming is running
curl http://localhost:8002/status

# Check Kafka topic
docker exec github-events-kafka kafka-console-consumer --topic github-events --bootstrap-server localhost:9092 --from-beginning
```

### API Errors
```bash
# Check service health
curl http://localhost:8000/services

# Check individual service health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## 🛑 Cleanup

```bash
# Stop all services
docker-compose -f docker-compose-microservices.yml down

# Remove all data (volumes)
docker-compose -f docker-compose-microservices.yml down -v

# Remove images
docker-compose -f docker-compose-microservices.yml down --rmi all
```

This microservices architecture gives you **complete control** over each component while keeping everything **containerized and isolated**!
