#!/bin/bash

# GitHub Events Real-time Processing Logs Script
set -e

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

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage
show_usage() {
    echo "Usage: $0 [service-name] [options]"
    echo
    echo "Available services:"
    echo "  zookeeper       - Zookeeper service"
    echo "  kafka           - Kafka broker"
    echo "  kafka-ui        - Kafka UI"
    echo "  minio           - MinIO object storage"
    echo "  spark-master    - Spark master node"
    echo "  spark-worker    - Spark worker node"
    echo "  github-producer - GitHub events producer"
    echo "  spark-consumer  - Spark streaming consumer"
    echo "  api             - REST API service"
    echo "  dashboard       - Web dashboard"
    echo "  all             - All services (default)"
    echo
    echo "Options:"
    echo "  -f, --follow    Follow log output (default)"
    echo "  --tail N        Number of lines to show from the end"
    echo "  --since TIME    Show logs since timestamp (e.g. 2013-01-02T13:23:37Z)"
    echo "  -h, --help      Show this help message"
    echo
    echo "Examples:"
    echo "  $0                          # Show logs for all services"
    echo "  $0 github-producer          # Show logs for producer only"
    echo "  $0 api --tail 100           # Show last 100 lines of API logs"
    echo "  $0 kafka --since 1h         # Show Kafka logs from last hour"
}

# Main function
main() {
    local service="all"
    local follow="-f"
    local tail=""
    local since=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -f|--follow)
                follow="-f"
                shift
                ;;
            --tail)
                if [[ -n $2 && $2 =~ ^[0-9]+$ ]]; then
                    tail="--tail $2"
                    shift 2
                else
                    print_error "Invalid tail value. Please provide a number."
                    exit 1
                fi
                ;;
            --since)
                if [[ -n $2 ]]; then
                    since="--since $2"
                    shift 2
                else
                    print_error "Invalid since value. Please provide a timestamp."
                    exit 1
                fi
                ;;
            zookeeper|kafka|kafka-ui|minio|minio-init|spark-master|spark-worker|github-producer|spark-consumer|api|dashboard|all)
                service=$1
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Map service names to container names
    case $service in
        zookeeper)
            service="github-events-zookeeper"
            ;;
        kafka)
            service="github-events-kafka"
            ;;
        kafka-ui)
            service="github-events-kafka-ui"
            ;;
        minio)
            service="github-events-minio"
            ;;
        minio-init)
            service="github-events-minio-init"
            ;;
        spark-master)
            service="github-events-spark-master"
            ;;
        spark-worker)
            service="github-events-spark-worker"
            ;;
        github-producer)
            service="github-events-producer"
            ;;
        spark-consumer)
            service="github-events-spark-consumer"
            ;;
        api)
            service="github-events-api"
            ;;
        dashboard)
            service="github-events-dashboard"
            ;;
        all)
            service=""
            ;;
    esac
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed."
        exit 1
    fi
    
    # Show logs
    print_status "Showing logs for ${service:-all services}..."
    echo "Press Ctrl+C to exit"
    echo "=================================="
    
    if [[ -n $service ]]; then
        # Show logs for specific service
        docker logs $follow $tail $since $service
    else
        # Show logs for all services
        docker-compose logs $follow $tail $since
    fi
}

# Run main function
main "$@"
