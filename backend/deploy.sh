#!/bin/bash

# SmartResume AI Resume Analyzer Deployment Script
# This script automates the deployment process for production environments

set -e  # Exit on any error

# Configuration
APP_NAME="smartresume-ai"
DOCKER_COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="./backups"
LOG_FILE="./logs/deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker is not running. Please start Docker service."
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        warning ".env file not found. Please copy .env.production to .env and configure it."
        if [ -f ".env.production" ]; then
            log "Copying .env.production to .env..."
            cp .env.production .env
            warning "Please edit .env file with your production configuration before continuing."
            read -p "Press Enter to continue after configuring .env file..."
        else
            error ".env.production template not found."
        fi
    fi
    
    success "Prerequisites check completed."
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p temp
    mkdir -p nginx/ssl
    mkdir -p monitoring
    mkdir -p "$BACKUP_DIR"
    
    success "Directories created."
}

# Backup current deployment
backup_current_deployment() {
    log "Creating backup of current deployment..."
    
    BACKUP_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_PATH="$BACKUP_DIR/backup_$BACKUP_TIMESTAMP"
    
    mkdir -p "$BACKUP_PATH"
    
    # Backup configuration files
    if [ -f ".env" ]; then
        cp .env "$BACKUP_PATH/"
    fi
    
    if [ -f "$DOCKER_COMPOSE_FILE" ]; then
        cp "$DOCKER_COMPOSE_FILE" "$BACKUP_PATH/"
    fi
    
    # Backup logs
    if [ -d "logs" ]; then
        cp -r logs "$BACKUP_PATH/"
    fi
    
    success "Backup created at $BACKUP_PATH"
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache
    
    success "Docker images built successfully."
}

# Deploy application
deploy_application() {
    log "Deploying application..."
    
    # Stop existing containers
    log "Stopping existing containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans
    
    # Start new containers
    log "Starting new containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    success "Application deployed successfully."
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Wait for services to start
    sleep 30
    
    # Check if containers are running
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
        error "Some containers are not running. Check logs with: docker-compose logs"
    fi
    
    # Check API health endpoint
    MAX_RETRIES=10
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -f http://localhost:8000/api/v1/health &> /dev/null; then
            success "Health check passed."
            return 0
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log "Health check attempt $RETRY_COUNT/$MAX_RETRIES failed. Retrying in 10 seconds..."
        sleep 10
    done
    
    error "Health check failed after $MAX_RETRIES attempts."
}

# Cleanup old images and containers
cleanup() {
    log "Cleaning up old Docker images and containers..."
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused containers
    docker container prune -f
    
    # Remove unused volumes (be careful with this in production)
    # docker volume prune -f
    
    success "Cleanup completed."
}

# Show deployment status
show_status() {
    log "Deployment Status:"
    echo "===================="
    
    # Show running containers
    echo "Running Containers:"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    
    echo ""
    echo "Service URLs:"
    echo "- API: http://localhost:8000"
    echo "- Health Check: http://localhost:8000/api/v1/health"
    echo "- API Documentation: http://localhost:8000/docs"
    
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "prometheus"; then
        echo "- Prometheus: http://localhost:9090"
    fi
    
    echo ""
    echo "Useful Commands:"
    echo "- View logs: docker-compose logs -f"
    echo "- Stop services: docker-compose down"
    echo "- Restart services: docker-compose restart"
    echo "- Update services: ./deploy.sh"
}

# Main deployment function
main() {
    log "Starting deployment of $APP_NAME..."
    
    check_prerequisites
    create_directories
    backup_current_deployment
    build_images
    deploy_application
    health_check
    cleanup
    show_status
    
    success "Deployment completed successfully!"
    log "Check the application at: http://localhost:8000/api/v1/health"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log "Stopping $APP_NAME..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" down
        success "Application stopped."
        ;;
    "restart")
        log "Restarting $APP_NAME..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" restart
        success "Application restarted."
        ;;
    "logs")
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
        ;;
    "status")
        show_status
        ;;
    "cleanup")
        cleanup
        ;;
    "health")
        health_check
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|status|cleanup|health}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Deploy the application (default)"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - Show and follow logs"
        echo "  status   - Show deployment status"
        echo "  cleanup  - Clean up old Docker resources"
        echo "  health   - Perform health check"
        exit 1
        ;;
esac