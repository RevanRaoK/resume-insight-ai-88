#!/bin/bash

# SmartResume AI Backend Deployment Script for Fly.io
# This script automates the deployment of the FastAPI backend service

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_APP_SUFFIX="prod"
CONFIG_FILE="fly-backend.toml"

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
    
    if [ ! -f "Dockerfile.backend" ]; then
        print_error "Dockerfile.backend not found in current directory."
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
    
    APP_NAME="smartresume-backend-$APP_SUFFIX"
    print_status "Using app name: $APP_NAME"
}

# Function to create fly configuration
create_fly_config() {
    print_status "Creating Fly.io configuration..."
    
    if [ ! -f "$CONFIG_FILE" ]; then
        if [ ! -f "fly.toml" ]; then
            print_error "fly.toml template not found. Please ensure the template exists."
            exit 1
        fi
        
        print_status "Copying fly.toml to $CONFIG_FILE..."
        cp fly.toml "$CONFIG_FILE"
    fi
    
    # Update app name in config file
    if command_exists sed; then
        sed -i.bak "s/smartresume-backend-\[YOUR-SUFFIX\]/$APP_NAME/g" "$CONFIG_FILE"
        rm -f "$CONFIG_FILE.bak"
        print_success "Updated app name in $CONFIG_FILE"
    else
        print_warning "sed not available. Please manually update app name in $CONFIG_FILE"
        print_warning "Change 'smartresume-backend-[YOUR-SUFFIX]' to '$APP_NAME'"
        read -p "Press Enter after updating the config file..."
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

# Function to set environment secrets
set_environment_secrets() {
    print_status "Setting up environment secrets..."
    
    # Check if secrets are already set
    if fly secrets list -a "$APP_NAME" | grep -q "DATABASE_URL"; then
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
    
    # DATABASE_URL
    read -p "DATABASE_URL (Supabase connection string): " DATABASE_URL
    if [ -n "$DATABASE_URL" ]; then
        fly secrets set DATABASE_URL="$DATABASE_URL" -a "$APP_NAME"
    fi
    
    # GOOGLE_API_KEY
    read -p "GOOGLE_API_KEY (Gemini API key): " GOOGLE_API_KEY
    if [ -n "$GOOGLE_API_KEY" ]; then
        fly secrets set GOOGLE_API_KEY="$GOOGLE_API_KEY" -a "$APP_NAME"
    fi
    
    # JWT_SECRET
    read -p "JWT_SECRET (or press Enter to generate): " JWT_SECRET
    if [ -z "$JWT_SECRET" ]; then
        JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "please-change-this-secret-$(date +%s)")
        print_status "Generated JWT_SECRET: $JWT_SECRET"
    fi
    fly secrets set JWT_SECRET="$JWT_SECRET" -a "$APP_NAME"
    
    # SUPABASE_URL
    read -p "SUPABASE_URL (Supabase project URL): " SUPABASE_URL
    if [ -n "$SUPABASE_URL" ]; then
        fly secrets set SUPABASE_URL="$SUPABASE_URL" -a "$APP_NAME"
    fi
    
    # SUPABASE_SERVICE_KEY
    read -p "SUPABASE_SERVICE_KEY (Supabase service role key): " SUPABASE_SERVICE_KEY
    if [ -n "$SUPABASE_SERVICE_KEY" ]; then
        fly secrets set SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY" -a "$APP_NAME"
    fi
    
    print_success "Environment secrets configured"
}

# Function to deploy the application
deploy_app() {
    print_status "Deploying backend application..."
    
    if fly deploy -c "$CONFIG_FILE"; then
        print_success "Backend deployment completed successfully!"
        
        # Show app status
        echo
        print_status "Application status:"
        fly status -a "$APP_NAME"
        
        # Test health endpoint
        echo
        print_status "Testing health endpoint..."
        sleep 10  # Wait for app to start
        
        APP_URL="https://$APP_NAME.fly.dev"
        if command_exists curl; then
            if curl -f "$APP_URL/api/v1/health" >/dev/null 2>&1; then
                print_success "Health check passed: $APP_URL/api/v1/health"
            else
                print_warning "Health check failed. App might still be starting up."
                print_status "You can check logs with: fly logs -a $APP_NAME"
            fi
        else
            print_status "curl not available. Please test manually: $APP_URL/api/v1/health"
        fi
        
        echo
        print_success "Backend service is available at: $APP_URL"
        print_status "Use this URL as VITE_API_URL when deploying the frontend"
        
    else
        print_error "Deployment failed!"
        print_status "Check logs with: fly logs -a $APP_NAME"
        exit 1
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
    echo "  $0              # Creates smartresume-backend-prod"
    echo "  $0 staging      # Creates smartresume-backend-staging"
    echo "  $0 dev          # Creates smartresume-backend-dev"
    echo
    echo "Environment Variables:"
    echo "  The script will prompt for required environment variables:"
    echo "  - DATABASE_URL"
    echo "  - GOOGLE_API_KEY"
    echo "  - JWT_SECRET (auto-generated if not provided)"
    echo "  - SUPABASE_URL"
    echo "  - SUPABASE_SERVICE_KEY"
}

# Main execution
main() {
    echo "=========================================="
    echo "SmartResume AI Backend Deployment Script"
    echo "=========================================="
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
    set_environment_secrets
    deploy_app
    
    echo
    print_success "Backend deployment process completed!"
    print_status "Next steps:"
    echo "  1. Test the backend API at https://$APP_NAME.fly.dev"
    echo "  2. Deploy the frontend using: ./scripts/deploy-frontend.sh"
    echo "  3. Monitor logs with: fly logs -a $APP_NAME"
}

# Run main function with all arguments
main "$@"