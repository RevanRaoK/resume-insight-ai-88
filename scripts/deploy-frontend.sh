#!/bin/bash

# SmartResume AI Frontend Deployment Script for Fly.io
# This script automates the deployment of the React frontend service

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_APP_SUFFIX="prod"
CONFIG_FILE="fly-frontend.toml"

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

# Check prerequisites
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
    
    if [ ! -f "Dockerfile.frontend" ]; then
        print_error "Dockerfile.frontend not found in current directory."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to get app suffix from user
get_app_suffix() {
    if [ -z "$1" ]; then
        read -p "Enter app suffix (default: $DEFAULT_APP_SUFFIX): " APP_SUFFIX
        APP_SUFFIX=${APP_SUFFIX:-$DEFAULT_APP_SUFFIX}
    else
        APP_SUFFIX="$1"
    fi
    
    APP_NAME="smartresume-frontend-$APP_SUFFIX"
    BACKEND_APP_NAME="smartresume-backend-$APP_SUFFIX"
    print_status "Using frontend app name: $APP_NAME"
    print_status "Expected backend app name: $BACKEND_APP_NAME"
}

# Function to create fly configuration
create_fly_config() {
    print_status "Creating Fly.io configuration..."
    
    if [ ! -f "$CONFIG_FILE" ]; then
        if [ ! -f "fly.toml" ]; then
            print_error "fly.toml template not found. Please ensure the template exists."
            exit 1
        fi
        
        print_status "Creating frontend configuration from template..."
        
        # Create frontend-specific config
        cat > "$CONFIG_FILE" << EOF
# Fly.io Configuration for SmartResume AI Frontend Service
app = "$APP_NAME"
primary_region = "ord"

[build]
  dockerfile = "Dockerfile.frontend"

[http_service]
  internal_port = 80
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 1
  processes = ["app"]

  [[http_service.checks]]
    grace_period = "10s"
    interval = "30s"
    method = "GET"
    timeout = "5s"
    path = "/"

[env]
  # Frontend environment variables will be set via secrets

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
EOF
        
        print_success "Created $CONFIG_FILE"
    else
        print_status "Using existing $CONFIG_FILE"
        
        # Update app name in existing config file
        if command_exists sed; then
            sed -i.bak "s/smartresume-frontend-\[YOUR-SUFFIX\]/$APP_NAME/g" "$CONFIG_FILE"
            rm -f "$CONFIG_FILE.bak"
            print_success "Updated app name in $CONFIG_FILE"
        fi
    fi
}

# Function to create app if it doesn't exist
create_app_if_needed() {
    print_status "Checking if app exists..."
    
    if fly apps list | grep -q "$APP_NAME"; then
        print_success "App $APP_NAME already exists"
    else
        print_status "Creating new app: $APP_NAME"
        fly apps create "$APP_NAME"
        print_success "Created app: $APP_NAME"
    fi
}

# Function to get backend URL
get_backend_url() {
    print_status "Determining backend URL..."
    
    # Check if backend app exists
    if fly apps list | grep -q "$BACKEND_APP_NAME"; then
        BACKEND_URL="https://$BACKEND_APP_NAME.fly.dev"
        print_success "Found backend app: $BACKEND_URL"
    else
        print_warning "Backend app $BACKEND_APP_NAME not found."
        read -p "Enter backend URL (e.g., https://smartresume-backend-prod.fly.dev): " BACKEND_URL
        
        if [ -z "$BACKEND_URL" ]; then
            print_error "Backend URL is required for frontend deployment."
            exit 1
        fi
    fi
    
    # Validate backend URL format
    if [[ ! "$BACKEND_URL" =~ ^https?:// ]]; then
        print_error "Backend URL must start with http:// or https://"
        exit 1
    fi
    
    print_status "Using backend URL: $BACKEND_URL"
}

# Function to set environment secrets
set_environment_secrets() {
    print_status "Setting up environment secrets..."
    
    # Check if secrets are already set
    if fly secrets list -a "$APP_NAME" | grep -q "VITE_API_URL"; then
        print_warning "Secrets appear to be already set. Skipping secret setup."
        read -p "Do you want to update secrets? (y/N): " UPDATE_SECRETS
        if [[ ! "$UPDATE_SECRETS" =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    echo
    print_status "Please provide the following environment variables:"
    echo "You can skip any that are already set by pressing Enter."
    echo
    
    # VITE_API_URL (use detected backend URL as default)
    read -p "VITE_API_URL (default: $BACKEND_URL): " INPUT_API_URL
    VITE_API_URL=${INPUT_API_URL:-$BACKEND_URL}
    fly secrets set VITE_API_URL="$VITE_API_URL" -a "$APP_NAME"
    
    # VITE_SUPABASE_URL
    read -p "VITE_SUPABASE_URL (Supabase project URL): " VITE_SUPABASE_URL
    if [ -n "$VITE_SUPABASE_URL" ]; then
        fly secrets set VITE_SUPABASE_URL="$VITE_SUPABASE_URL" -a "$APP_NAME"
    fi
    
    # VITE_SUPABASE_ANON_KEY
    read -p "VITE_SUPABASE_ANON_KEY (Supabase anonymous key): " VITE_SUPABASE_ANON_KEY
    if [ -n "$VITE_SUPABASE_ANON_KEY" ]; then
        fly secrets set VITE_SUPABASE_ANON_KEY="$VITE_SUPABASE_ANON_KEY" -a "$APP_NAME"
    fi
    
    print_success "Environment secrets configured"
}

# Function to deploy the application
deploy_app() {
    print_status "Deploying frontend application..."
    
    if fly deploy -c "$CONFIG_FILE"; then
        print_success "Frontend deployment completed successfully!"
        
        # Show app status
        echo
        print_status "Application status:"
        fly status -a "$APP_NAME"
        
        # Test frontend
        echo
        print_status "Testing frontend..."
        sleep 10  # Wait for app to start
        
        APP_URL="https://$APP_NAME.fly.dev"
        if command_exists curl; then
            if curl -f "$APP_URL" >/dev/null 2>&1; then
                print_success "Frontend is accessible: $APP_URL"
            else
                print_warning "Frontend test failed. App might still be starting up."
                print_status "You can check logs with: fly logs -a $APP_NAME"
            fi
        else
            print_status "curl not available. Please test manually: $APP_URL"
        fi
        
        echo
        print_success "Frontend service is available at: $APP_URL"
        
    else
        print_error "Deployment failed!"
        print_status "Check logs with: fly logs -a $APP_NAME"
        exit 1
    fi
}

# Function to verify backend connectivity
verify_backend_connectivity() {
    print_status "Verifying backend connectivity..."
    
    if command_exists curl; then
        if curl -f "$VITE_API_URL/api/v1/health" >/dev/null 2>&1; then
            print_success "Backend is accessible from: $VITE_API_URL"
        else
            print_warning "Cannot reach backend at: $VITE_API_URL"
            print_warning "Please ensure the backend is deployed and accessible"
        fi
    else
        print_status "curl not available. Please verify backend manually: $VITE_API_URL/api/v1/health"
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [app-suffix]"
    echo
    echo "Options:"
    echo "  app-suffix    Suffix for the app name (default: $DEFAULT_APP_SUFFIX)"
    echo
    echo "Examples:"
    echo "  $0              # Creates smartresume-frontend-prod"
    echo "  $0 staging      # Creates smartresume-frontend-staging"
    echo "  $0 dev          # Creates smartresume-frontend-dev"
    echo
    echo "Environment Variables:"
    echo "  The script will prompt for required environment variables:"
    echo "  - VITE_API_URL (backend service URL)"
    echo "  - VITE_SUPABASE_URL"
    echo "  - VITE_SUPABASE_ANON_KEY"
    echo
    echo "Prerequisites:"
    echo "  - Backend service should be deployed first"
    echo "  - Supabase project should be configured"
}

# Main execution
main() {
    echo "==========================================="
    echo "SmartResume AI Frontend Deployment Script"
    echo "==========================================="
    echo
    
    # Handle help flag
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        show_usage
        exit 0
    fi
    
    # Execute deployment steps
    check_prerequisites
    get_app_suffix "$1"
    create_fly_config
    create_app_if_needed
    get_backend_url
    set_environment_secrets
    deploy_app
    verify_backend_connectivity
    
    echo
    print_success "Frontend deployment process completed!"
    print_status "Next steps:"
    echo "  1. Test the application at https://$APP_NAME.fly.dev"
    echo "  2. Configure custom domains if needed"
    echo "  3. Monitor logs with: fly logs -a $APP_NAME"
    echo "  4. Monitor backend logs with: fly logs -a $BACKEND_APP_NAME"
}

# Run main function with all arguments
main "$@"