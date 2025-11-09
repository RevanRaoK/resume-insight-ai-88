#!/bin/bash

# SmartResume AI Complete Deployment Script for Fly.io
# This script automates the deployment of both backend and frontend services

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_APP_SUFFIX="prod"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [options] [app-suffix]"
    echo
    echo "Options:"
    echo "  -b, --backend-only    Deploy only the backend service"
    echo "  -f, --frontend-only   Deploy only the frontend service"
    echo "  -h, --help           Show this help message"
    echo
    echo "Arguments:"
    echo "  app-suffix           Suffix for the app names (default: $DEFAULT_APP_SUFFIX)"
    echo
    echo "Examples:"
    echo "  $0                   # Deploy both services with 'prod' suffix"
    echo "  $0 staging           # Deploy both services with 'staging' suffix"
    echo "  $0 -b prod           # Deploy only backend with 'prod' suffix"
    echo "  $0 -f staging        # Deploy only frontend with 'staging' suffix"
    echo
    echo "This script will:"
    echo "  1. Check prerequisites (Fly.io CLI, authentication, Dockerfiles)"
    echo "  2. Deploy backend service (if not skipped)"
    echo "  3. Deploy frontend service (if not skipped)"
    echo "  4. Verify both services are working"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists fly; then
        print_error "Fly.io CLI not found. Please install it from https://fly.io/docs/getting-started/installing-flyctl/"
        exit 1
    fi
    
    if ! fly auth whoami >/dev/null 2>&1; then
        print_error "Not logged in to Fly.io. Please run 'fly auth login' first."
        exit 1
    fi
    
    # Check for deployment scripts
    if [ ! -f "$SCRIPT_DIR/deploy-backend.sh" ]; then
        print_error "Backend deployment script not found: $SCRIPT_DIR/deploy-backend.sh"
        exit 1
    fi
    
    if [ ! -f "$SCRIPT_DIR/deploy-frontend.sh" ]; then
        print_error "Frontend deployment script not found: $SCRIPT_DIR/deploy-frontend.sh"
        exit 1
    fi
    
    # Make scripts executable
    chmod +x "$SCRIPT_DIR/deploy-backend.sh"
    chmod +x "$SCRIPT_DIR/deploy-frontend.sh"
    
    print_success "Prerequisites check passed"
}

# Function to deploy backend
deploy_backend() {
    echo
    echo "=========================================="
    echo "DEPLOYING BACKEND SERVICE"
    echo "=========================================="
    
    if "$SCRIPT_DIR/deploy-backend.sh" "$APP_SUFFIX"; then
        print_success "Backend deployment completed successfully"
        BACKEND_DEPLOYED=true
    else
        print_error "Backend deployment failed"
        exit 1
    fi
}

# Function to deploy frontend
deploy_frontend() {
    echo
    echo "=========================================="
    echo "DEPLOYING FRONTEND SERVICE"
    echo "=========================================="
    
    if "$SCRIPT_DIR/deploy-frontend.sh" "$APP_SUFFIX"; then
        print_success "Frontend deployment completed successfully"
        FRONTEND_DEPLOYED=true
    else
        print_error "Frontend deployment failed"
        exit 1
    fi
}

# Function to verify deployment
verify_deployment() {
    echo
    echo "=========================================="
    echo "VERIFYING DEPLOYMENT"
    echo "=========================================="
    
    BACKEND_APP="smartresume-backend-$APP_SUFFIX"
    FRONTEND_APP="smartresume-frontend-$APP_SUFFIX"
    
    if [ "$BACKEND_DEPLOYED" = true ]; then
        print_status "Checking backend service..."
        BACKEND_URL="https://$BACKEND_APP.fly.dev"
        
        if command_exists curl; then
            if curl -f "$BACKEND_URL/api/v1/health" >/dev/null 2>&1; then
                print_success "✓ Backend health check passed: $BACKEND_URL"
            else
                print_warning "✗ Backend health check failed: $BACKEND_URL"
            fi
        fi
        
        print_status "Backend status:"
        fly status -a "$BACKEND_APP" | head -10
    fi
    
    if [ "$FRONTEND_DEPLOYED" = true ]; then
        print_status "Checking frontend service..."
        FRONTEND_URL="https://$FRONTEND_APP.fly.dev"
        
        if command_exists curl; then
            if curl -f "$FRONTEND_URL" >/dev/null 2>&1; then
                print_success "✓ Frontend accessibility check passed: $FRONTEND_URL"
            else
                print_warning "✗ Frontend accessibility check failed: $FRONTEND_URL"
            fi
        fi
        
        print_status "Frontend status:"
        fly status -a "$FRONTEND_APP" | head -10
    fi
}

# Function to show deployment summary
show_summary() {
    echo
    echo "=========================================="
    echo "DEPLOYMENT SUMMARY"
    echo "=========================================="
    
    if [ "$BACKEND_DEPLOYED" = true ]; then
        echo "✓ Backend Service:"
        echo "  App Name: smartresume-backend-$APP_SUFFIX"
        echo "  URL: https://smartresume-backend-$APP_SUFFIX.fly.dev"
        echo "  Health: https://smartresume-backend-$APP_SUFFIX.fly.dev/api/v1/health"
    fi
    
    if [ "$FRONTEND_DEPLOYED" = true ]; then
        echo "✓ Frontend Service:"
        echo "  App Name: smartresume-frontend-$APP_SUFFIX"
        echo "  URL: https://smartresume-frontend-$APP_SUFFIX.fly.dev"
    fi
    
    echo
    echo "Useful Commands:"
    
    if [ "$BACKEND_DEPLOYED" = true ]; then
        echo "  Backend logs:  fly logs -a smartresume-backend-$APP_SUFFIX"
        echo "  Backend scale: fly scale memory 1024 -a smartresume-backend-$APP_SUFFIX"
    fi
    
    if [ "$FRONTEND_DEPLOYED" = true ]; then
        echo "  Frontend logs: fly logs -a smartresume-frontend-$APP_SUFFIX"
        echo "  Frontend scale: fly scale memory 512 -a smartresume-frontend-$APP_SUFFIX"
    fi
    
    echo
    echo "Next Steps:"
    echo "  1. Test the application functionality"
    echo "  2. Configure custom domains (optional)"
    echo "  3. Set up monitoring and alerts"
    echo "  4. Configure CI/CD for automated deployments"
}

# Parse command line arguments
BACKEND_ONLY=false
FRONTEND_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        -f|--frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            APP_SUFFIX="$1"
            shift
            ;;
    esac
done

# Set default app suffix if not provided
APP_SUFFIX=${APP_SUFFIX:-$DEFAULT_APP_SUFFIX}

# Validate conflicting options
if [ "$BACKEND_ONLY" = true ] && [ "$FRONTEND_ONLY" = true ]; then
    print_error "Cannot specify both --backend-only and --frontend-only"
    exit 1
fi

# Main execution
main() {
    echo "=============================================="
    echo "SmartResume AI Complete Deployment Script"
    echo "=============================================="
    echo
    print_status "App suffix: $APP_SUFFIX"
    
    if [ "$BACKEND_ONLY" = true ]; then
        print_status "Mode: Backend only"
    elif [ "$FRONTEND_ONLY" = true ]; then
        print_status "Mode: Frontend only"
    else
        print_status "Mode: Full deployment (backend + frontend)"
    fi
    
    echo
    
    # Initialize deployment flags
    BACKEND_DEPLOYED=false
    FRONTEND_DEPLOYED=false
    
    # Check prerequisites
    check_prerequisites
    
    # Deploy services based on options
    if [ "$FRONTEND_ONLY" != true ]; then
        deploy_backend
    fi
    
    if [ "$BACKEND_ONLY" != true ]; then
        deploy_frontend
    fi
    
    # Verify deployment
    verify_deployment
    
    # Show summary
    show_summary
    
    echo
    print_success "Deployment process completed!"
}

# Run main function
main