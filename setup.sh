#!/bin/bash

# GitHub Events Pipeline - Minimal Setup
set -e

echo "🚀 Setting up GitHub Events Pipeline..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    print_status "Checking Docker..."
    
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

# Create Kafka topic
create_kafka_topic() {
    print_status "Creating Kafka topic..."
    
    docker exec kafka kafka-topics --create \
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

# Start services
start_services() {
    print_status "Starting services..."
    
    docker-compose up -d
    
    print_status "Waiting for services to be ready..."
    sleep 30
    
    print_success "Services started"
}

# Start data pipeline
start_pipeline() {
    print_status "Starting data pipeline..."
    
    # Start producer
    curl -sS -X POST http://localhost:8001/start
    print_success "Producer started"
    
    # Start streaming
    curl -sS -X POST http://localhost:8002/start
    print_success "Streaming started"
}

# Show status
show_status() {
    print_success "🎉 GitHub Events Pipeline is ready!"
    echo
    echo "📊 Service URLs:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 Dashboard:              http://localhost:8080"
    echo "📤 Producer API:           http://localhost:8001"
    echo "⚡ Streaming API:          http://localhost:8002"
    echo "🔍 Query API:              http://localhost:8003"
    echo "📋 Kafka UI:               http://localhost:8081"
    echo "   └─ Topics:              http://localhost:8081/ui/clusters/local/all-topics"
    echo "   └─ GitHub Events:       http://localhost:8081/ui/clusters/local/topics/github-events"
    echo
    echo "🛠️  Management:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "View logs:    docker-compose logs -f [service]"
    echo "Stop all:     docker-compose down"
    echo "Restart:      docker-compose restart [service]"
    echo
    if [ -z "$GITHUB_TOKEN" ]; then
        print_warning "Set GITHUB_TOKEN environment variable for better rate limits"
    fi
}

# Main function
main() {
    echo "GitHub Events Pipeline Setup"
    echo "============================"
    echo
    
    check_docker
    start_services
    create_kafka_topic
    start_pipeline
    
    echo
    show_status
}

# Run main function
main "$@"
