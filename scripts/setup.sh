#!/bin/bash

# GitHub Events Real-time Processing Setup Script
set -e

echo "🚀 Setting up GitHub Events Real-time Processing System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if Docker is installed and running
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
    
    print_success "Docker is installed and running"
}

# Check if Docker Compose is installed
check_docker_compose() {
    print_status "Checking Docker Compose installation..."
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker Compose is installed"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p iceberg/warehouse
    mkdir -p iceberg/checkpoints
    mkdir -p logs
    
    print_success "Directories created"
}

# Set up environment files
setup_environment() {
    print_status "Setting up environment configuration..."
    
    # Create .env file for producer if it doesn't exist
    if [ ! -f producer/.env ]; then
        cat > producer/.env << EOF
# GitHub API Configuration
GITHUB_TOKEN=

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=github-events

# Producer Configuration
FETCH_INTERVAL_SECONDS=30
MAX_EVENTS_PER_FETCH=100
EOF
        print_warning "Created producer/.env file. Please add your GitHub token for better rate limits."
    fi
    
    # Create .env file for API if it doesn't exist
    if [ ! -f api/.env ]; then
        cat > api/.env << EOF
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Spark Configuration
SPARK_MASTER=spark://spark-master:7077

# Storage Configuration
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
ICEBERG_WAREHOUSE_PATH=s3a://iceberg/warehouse
EOF
    fi
    
    # Create .env file for Spark if it doesn't exist
    if [ ! -f spark/.env ]; then
        cat > spark/.env << EOF
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC=github-events
KAFKA_STARTING_OFFSETS=latest

# Spark Configuration
SPARK_MASTER=spark://spark-master:7077

# Storage Configuration
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_BUCKET=iceberg
ICEBERG_WAREHOUSE_PATH=s3a://iceberg/warehouse
CHECKPOINT_LOCATION=s3a://iceberg/checkpoints
EOF
    fi
    
    print_success "Environment configuration completed"
}

# Build Docker images
build_images() {
    print_status "Building Docker images..."
    
    docker-compose build --parallel
    
    print_success "Docker images built successfully"
}

# Start infrastructure services
start_infrastructure() {
    print_status "Starting infrastructure services (Zookeeper, Kafka, MinIO, Spark)..."
    
    docker-compose up -d zookeeper kafka minio minio-init spark-master spark-worker
    
    # Wait for services to be healthy
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    check_service_health "zookeeper" "2181"
    check_service_health "kafka" "9092"
    check_service_health "minio" "9000"
    check_service_health "spark-master" "8080"
    
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
        --config retention.ms=7200000 \
        --config segment.ms=3600000 \
        --config cleanup.policy=delete \
        --if-not-exists
    
    print_success "Kafka topic created"
}

# Start application services
start_applications() {
    print_status "Starting application services..."
    
    docker-compose up -d github-producer spark-consumer api dashboard
    
    print_success "Application services started"
}

# Display service URLs
show_services() {
    print_success "🎉 GitHub Events Real-time Processing System is ready!"
    echo
    echo "Service URLs:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Dashboard:           http://localhost:8080"
    echo "🔌 REST API:            http://localhost:8000"
    echo "📈 API Documentation:   http://localhost:8000/docs"
    echo "⚡ Kafka UI:            http://localhost:8090"
    echo "🗄️  MinIO Console:       http://localhost:9001"
    echo "⚙️  Spark Master UI:     http://localhost:8080"
    echo
    echo "Default Credentials:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "MinIO: minioadmin / minioadmin123"
    echo
    echo "Useful Commands:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "View logs:              docker-compose logs -f [service-name]"
    echo "Stop all services:      docker-compose down"
    echo "Restart service:        docker-compose restart [service-name]"
    echo "View service status:    docker-compose ps"
    echo
}

# Main setup function
main() {
    echo "GitHub Events Real-time Processing System Setup"
    echo "=============================================="
    echo
    
    check_docker
    check_docker_compose
    create_directories
    setup_environment
    build_images
    start_infrastructure
    create_kafka_topic
    start_applications
    
    echo
    print_status "Waiting for all services to be fully ready..."
    sleep 20
    
    show_services
    
    print_warning "Note: It may take a few minutes for all services to be fully operational."
    print_warning "If you have a GitHub token, add it to producer/.env for better rate limits."
}

# Run main function
main "$@"
