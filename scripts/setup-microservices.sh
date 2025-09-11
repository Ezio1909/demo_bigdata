#!/bin/bash

# Microservices Setup Script - Containerized Architecture
set -e

echo "🐳 Setting up GitHub Events Microservices Architecture..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Docker
check_docker() {
    print_status "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are ready"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p iceberg/warehouse
    mkdir -p iceberg/checkpoints
    mkdir -p logs
    
    print_success "Directories created"
}

# Create environment files
setup_environment() {
    print_status "Setting up environment configuration..."
    
    # Producer .env
    if [ ! -f producer/.env ]; then
        cat > producer/.env << EOF
# GitHub API Configuration
GITHUB_TOKEN=

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC=github-events

# Producer Configuration
FETCH_INTERVAL_SECONDS=3
MAX_EVENTS_PER_FETCH=100
PRODUCER_API_PORT=8001
EOF
        print_warning "Created producer/.env - Add your GitHub token for better rate limits"
    fi
    
    # Spark .env
    cat > spark/.env << EOF
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC=github-events
KAFKA_STARTING_OFFSETS=latest

# Spark Configuration
SPARK_MASTER=local[*]

# Storage Configuration
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_BUCKET=iceberg
ICEBERG_WAREHOUSE_PATH=s3a://iceberg/warehouse
CHECKPOINT_LOCATION=s3a://iceberg/checkpoints
STREAMING_API_PORT=8002
EOF
    
    # API .env
    cat > api/.env << EOF
# API Configuration
API_HOST=0.0.0.0
API_PORT=8003

# Spark Configuration
SPARK_MASTER=local[*]

# Storage Configuration
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
ICEBERG_WAREHOUSE_PATH=s3a://iceberg/warehouse
EOF
    
    print_success "Environment configuration completed"
}

# Build Docker images
build_images() {
    print_status "Building Docker images..."
    
    docker-compose -f docker-compose-microservices.yml build --parallel
    
    print_success "Docker images built successfully"
}

# Start infrastructure services
start_infrastructure() {
    print_status "Starting infrastructure services (Zookeeper, Kafka, MinIO)..."
    
    docker-compose -f docker-compose-microservices.yml up -d zookeeper kafka minio minio-init
    
    # Wait for services to be healthy
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    check_service_health "kafka" "9092"
    check_service_health "minio" "9000"
    
    print_success "Infrastructure services are running"
}

# Check service health
check_service_health() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Checking $service health..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            print_success "$service is healthy"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service failed to start properly"
    return 1
}

# Create Kafka topic
create_kafka_topic() {
    print_status "Creating Kafka topic..."
    
    docker exec github-events-kafka kafka-topics --create \
        --topic github-events \
        --bootstrap-server localhost:9092 \
        --partitions 3 \
        --replication-factor 1 \
        --config retention.ms=10800000 \
        --config segment.ms=3600000 \
        --config cleanup.policy=delete \
        --if-not-exists
    
    print_success "Kafka topic created"
}

# Start microservices
start_microservices() {
    print_status "Starting microservices..."
    
    docker-compose -f docker-compose-microservices.yml up -d \
        github-producer-service \
        spark-streaming-service \
        data-query-service \
        dashboard-service \
        service-registry \
        kafka-ui
    
    print_success "Microservices started"
}

# Display service URLs and instructions
show_services() {
    print_success "🎉 GitHub Events Microservices Architecture is ready!"
    echo
    echo "📊 Service URLs:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 Dashboard:              http://localhost:8080"
    echo "📋 Service Registry:       http://localhost:8000"
    echo "📤 Producer API:           http://localhost:8001"
    echo "⚡ Streaming API:          http://localhost:8002"
    echo "🔍 Query API:              http://localhost:8003"
    echo "⚡ Kafka UI:               http://localhost:8090"
    echo "🗄️  MinIO Console:         http://localhost:9001"
    echo
    echo "🔑 Default Credentials:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "MinIO: minioadmin / minioadmin123"
    echo
    echo "🚀 How to Start the Pipeline:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "1. Start Producer:"
    echo "   curl -X POST http://localhost:8001/start"
    echo
    echo "2. Start Streaming:"
    echo "   curl -X POST http://localhost:8002/start"
    echo
    echo "3. Check Status:"
    echo "   curl http://localhost:8000/services"
    echo
    echo "📚 API Documentation:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Producer API:    http://localhost:8001/docs"
    echo "Streaming API:   http://localhost:8002/docs"
    echo "Query API:       http://localhost:8003/docs"
    echo "Registry API:    http://localhost:8000/docs"
    echo
    echo "🛠️  Management Commands:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "View logs:       docker-compose -f docker-compose-microservices.yml logs -f [service]"
    echo "Stop all:        docker-compose -f docker-compose-microservices.yml down"
    echo "Restart service: docker-compose -f docker-compose-microservices.yml restart [service]"
    echo "Check status:    docker-compose -f docker-compose-microservices.yml ps"
    echo
    print_warning "Note: It may take 1-2 minutes for all services to be fully operational."
    print_warning "Add your GitHub token to producer/.env for better rate limits."
}

# Main setup function
main() {
    echo "GitHub Events Microservices Setup"
    echo "================================="
    echo
    
    check_docker
    create_directories
    setup_environment
    build_images
    start_infrastructure
    create_kafka_topic
    start_microservices
    
    echo
    print_status "Waiting for all services to be fully ready..."
    sleep 20
    
    show_services
}

# Run main function
main "$@"
