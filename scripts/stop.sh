#!/bin/bash

# GitHub Events Real-time Processing Stop Script
set -e

echo "🛑 Stopping GitHub Events Real-time Processing System..."

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

# Stop all services
stop_services() {
    print_status "Stopping all services..."
    
    if docker-compose ps -q | grep -q .; then
        docker-compose down
        print_success "All services stopped"
    else
        print_warning "No services were running"
    fi
}

# Clean up containers and networks
cleanup() {
    print_status "Cleaning up containers and networks..."
    
    # Remove stopped containers
    docker container prune -f
    
    # Remove unused networks
    docker network prune -f
    
    print_success "Cleanup completed"
}

# Remove volumes (optional)
remove_volumes() {
    if [ "$1" = "--volumes" ] || [ "$1" = "-v" ]; then
        print_warning "Removing all data volumes..."
        read -p "Are you sure you want to remove all data? This cannot be undone. (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v
            docker volume prune -f
            print_success "Volumes removed"
        else
            print_status "Volume removal cancelled"
        fi
    fi
}

# Main stop function
main() {
    echo "GitHub Events System Shutdown"
    echo "============================"
    echo
    
    stop_services
    remove_volumes "$1"
    cleanup
    
    echo
    print_success "🎉 GitHub Events System has been stopped successfully!"
    echo
    echo "To start the system again, run:"
    echo "  ./scripts/setup.sh"
    echo
    echo "To remove all data volumes, run:"
    echo "  ./scripts/stop.sh --volumes"
    echo
}

# Run main function
main "$@"
