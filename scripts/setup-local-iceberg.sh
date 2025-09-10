#!/bin/bash

# Setup script for LOCAL FILESYSTEM Iceberg (data will be in ./iceberg/ directory)
set -e

echo "🗄️  Setting up GitHub Events with LOCAL Iceberg Storage..."

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
    
    print_success "Docker is ready"
}

# Create local Iceberg directories
create_iceberg_directories() {
    print_status "Creating local Iceberg directories..."
    
    mkdir -p iceberg/warehouse
    mkdir -p iceberg/checkpoints
    mkdir -p iceberg/metadata
    
    # Set proper permissions
    chmod -R 755 iceberg/
    
    print_success "Local Iceberg directories created:"
    echo "  📁 ./iceberg/warehouse   - Iceberg table data"
    echo "  📁 ./iceberg/checkpoints - Spark streaming checkpoints"
    echo "  📁 ./iceberg/metadata    - Table metadata"
}

# Create environment files for local setup
setup_local_environment() {
    print_status "Setting up local environment configuration..."
    
    # Producer .env (same as before)
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
        print_warning "Created producer/.env - Add your GitHub token for better rate limits"
    fi
    
    # Spark .env for LOCAL filesystem
    cat > spark/.env << EOF
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC=github-events
KAFKA_STARTING_OFFSETS=latest

# Spark Configuration
SPARK_MASTER=spark://spark-master:7077

# LOCAL ICEBERG Configuration
USE_LOCAL_FILESYSTEM=true
ICEBERG_WAREHOUSE_PATH=file:///opt/iceberg/warehouse
CHECKPOINT_LOCATION=file:///opt/iceberg/checkpoints
EOF
    
    # API .env for LOCAL filesystem
    cat > api/.env << EOF
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Spark Configuration
SPARK_MASTER=spark://spark-master:7077

# LOCAL ICEBERG Configuration
USE_LOCAL_FILESYSTEM=true
ICEBERG_WAREHOUSE_PATH=file:///opt/iceberg/warehouse
EOF
    
    print_success "Environment configured for LOCAL Iceberg storage"
}

# Update Spark config to use local version
setup_spark_config() {
    print_status "Configuring Spark for local Iceberg..."
    
    # Backup original config
    if [ -f spark/spark_config.py ] && [ ! -f spark/spark_config.py.backup ]; then
        cp spark/spark_config.py spark/spark_config.py.backup
    fi
    
    # Use local config
    cp spark/spark_config_local.py spark/spark_config.py
    
    print_success "Spark configured for local filesystem Iceberg"
}

# Start services with local Iceberg
start_local_services() {
    print_status "Starting services with LOCAL Iceberg storage..."
    
    # Use the local Iceberg docker-compose file
    docker-compose -f docker-compose-local-iceberg.yml up -d
    
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check core services
    check_service_health "kafka" "9092"
    check_service_health "spark-master" "8080"
    
    print_success "Services are running with LOCAL Iceberg storage"
}

check_service_health() {
    local service=$1
    local port=$2
    local max_attempts=15
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

# Show final information
show_local_setup_info() {
    print_success "🎉 LOCAL Iceberg setup complete!"
    echo
    echo "📁 Your Iceberg data will be stored in:"
    echo "   ./iceberg/warehouse/    - Table data files (Parquet)"
    echo "   ./iceberg/checkpoints/  - Spark streaming state"
    echo "   ./iceberg/metadata/     - Table metadata"
    echo
    echo "🔗 Service URLs:"
    echo "   Kafka UI:       http://localhost:8090"
    echo "   Spark Master:   http://localhost:8080"  
    echo "   API (optional): http://localhost:8000"
    echo
    echo "📊 Monitor your data:"
    echo "   ls -la ./iceberg/warehouse/"
    echo "   docker logs github-events-spark-consumer"
    echo "   docker logs github-events-producer"
    echo
    echo "🛑 To stop:"
    echo "   docker-compose -f docker-compose-local-iceberg.yml down"
    echo
    print_warning "Note: It may take 1-2 minutes for data to appear in ./iceberg/"
}

# Main function
main() {
    echo "LOCAL Iceberg Setup for GitHub Events"
    echo "====================================="
    echo
    
    check_docker
    create_iceberg_directories
    setup_local_environment
    setup_spark_config
    start_local_services
    create_kafka_topic
    
    echo
    show_local_setup_info
}

# Run main function
main "$@"
