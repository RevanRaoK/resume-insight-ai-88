# SmartResume AI Deployment Script for Fly.io (PowerShell)
# This script automates the deployment of both backend and frontend services

param(
    [string]$AppSuffix = "prod",
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$Help
)

# Configuration
$ErrorActionPreference = "Stop"

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Cyan"
}

function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

function Show-Usage {
    Write-Host "SmartResume AI Deployment Script for Fly.io"
    Write-Host ""
    Write-Host "Usage: .\deploy.ps1 [options]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -AppSuffix <suffix>   Suffix for the app names (default: prod)"
    Write-Host "  -BackendOnly          Deploy only the backend service"
    Write-Host "  -FrontendOnly         Deploy only the frontend service"
    Write-Host "  -Help                 Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\deploy.ps1                    # Deploy both services with 'prod' suffix"
    Write-Host "  .\deploy.ps1 -AppSuffix staging # Deploy both services with 'staging' suffix"
    Write-Host "  .\deploy.ps1 -BackendOnly       # Deploy only backend"
    Write-Host "  .\deploy.ps1 -FrontendOnly      # Deploy only frontend"
}

function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check if fly command exists
    try {
        $null = Get-Command fly -ErrorAction Stop
    }
    catch {
        Write-Error "Fly.io CLI not found. Please install it from https://fly.io/docs/getting-started/installing-flyctl/"
        exit 1
    }
    
    # Check if logged in to Fly.io
    try {
        $null = fly auth whoami 2>$null
    }
    catch {
        Write-Error "Not logged in to Fly.io. Please run 'fly auth login' first."
        exit 1
    }
    
    Write-Success "Prerequisites check passed"
}

function Deploy-Backend {
    param([string]$Suffix)
    
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor $Colors.Blue
    Write-Host "DEPLOYING BACKEND SERVICE" -ForegroundColor $Colors.Blue
    Write-Host "==========================================" -ForegroundColor $Colors.Blue
    
    $AppName = "smartresume-backend-$Suffix"
    $ConfigFile = "fly-backend.toml"
    
    Write-Status "Using backend app name: $AppName"
    
    # Check if Dockerfile exists
    if (-not (Test-Path "Dockerfile.backend")) {
        Write-Error "Dockerfile.backend not found in current directory."
        exit 1
    }
    
    # Create fly configuration
    Write-Status "Creating Fly.io configuration..."
    
    if (-not (Test-Path $ConfigFile)) {
        if (-not (Test-Path "fly.toml")) {
            Write-Error "fly.toml template not found. Please ensure the template exists."
            exit 1
        }
        
        Write-Status "Copying fly.toml to $ConfigFile..."
        Copy-Item "fly.toml" $ConfigFile
    }
    
    # Update app name in config file
    $content = Get-Content $ConfigFile
    $content = $content -replace 'smartresume-backend-\[YOUR-SUFFIX\]', $AppName
    $content | Set-Content $ConfigFile
    Write-Success "Updated app name in $ConfigFile"
    
    # Check if app exists
    Write-Status "Checking if app exists..."
    $appExists = fly apps list | Select-String $AppName
    
    if (-not $appExists) {
        Write-Status "Creating new app: $AppName"
        fly apps create $AppName
        Write-Success "Created app: $AppName"
    } else {
        Write-Success "App $AppName already exists"
    }
    
    # Set environment secrets
    Write-Status "Setting up environment secrets..."
    Write-Host ""
    Write-Host "Please provide the following environment variables:"
    Write-Host "You can skip any that are already set by pressing Enter."
    Write-Host ""
    
    $DatabaseUrl = Read-Host "DATABASE_URL (Supabase connection string)"
    if ($DatabaseUrl) {
        fly secrets set "DATABASE_URL=$DatabaseUrl" -a $AppName
    }
    
    $GoogleApiKey = Read-Host "GOOGLE_API_KEY (Gemini API key)"
    if ($GoogleApiKey) {
        fly secrets set "GOOGLE_API_KEY=$GoogleApiKey" -a $AppName
    }
    
    $JwtSecret = Read-Host "JWT_SECRET (or press Enter to generate)"
    if (-not $JwtSecret) {
        $JwtSecret = [System.Web.Security.Membership]::GeneratePassword(32, 8)
        Write-Status "Generated JWT_SECRET: $JwtSecret"
    }
    fly secrets set "JWT_SECRET=$JwtSecret" -a $AppName
    
    $SupabaseUrl = Read-Host "SUPABASE_URL (Supabase project URL)"
    if ($SupabaseUrl) {
        fly secrets set "SUPABASE_URL=$SupabaseUrl" -a $AppName
    }
    
    $SupabaseServiceKey = Read-Host "SUPABASE_SERVICE_KEY (Supabase service role key)"
    if ($SupabaseServiceKey) {
        fly secrets set "SUPABASE_SERVICE_KEY=$SupabaseServiceKey" -a $AppName
    }
    
    Write-Success "Environment secrets configured"
    
    # Deploy the application
    Write-Status "Deploying backend application..."
    
    try {
        fly deploy -c $ConfigFile
        Write-Success "Backend deployment completed successfully!"
        
        # Show app status
        Write-Host ""
        Write-Status "Application status:"
        fly status -a $AppName
        
        # Test health endpoint
        Write-Host ""
        Write-Status "Testing health endpoint..."
        Start-Sleep -Seconds 10
        
        $AppUrl = "https://$AppName.fly.dev"
        try {
            $response = Invoke-WebRequest -Uri "$AppUrl/api/v1/health" -Method Get -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                Write-Success "Health check passed: $AppUrl/api/v1/health"
            }
        }
        catch {
            Write-Warning "Health check failed. App might still be starting up."
            Write-Status "You can check logs with: fly logs -a $AppName"
        }
        
        Write-Host ""
        Write-Success "Backend service is available at: $AppUrl"
        Write-Status "Use this URL as VITE_API_URL when deploying the frontend"
        
        return $true
    }
    catch {
        Write-Error "Deployment failed!"
        Write-Status "Check logs with: fly logs -a $AppName"
        return $false
    }
}

function Deploy-Frontend {
    param([string]$Suffix)
    
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor $Colors.Blue
    Write-Host "DEPLOYING FRONTEND SERVICE" -ForegroundColor $Colors.Blue
    Write-Host "==========================================" -ForegroundColor $Colors.Blue
    
    $AppName = "smartresume-frontend-$Suffix"
    $BackendAppName = "smartresume-backend-$Suffix"
    $ConfigFile = "fly-frontend.toml"
    
    Write-Status "Using frontend app name: $AppName"
    Write-Status "Expected backend app name: $BackendAppName"
    
    # Check if Dockerfile exists
    if (-not (Test-Path "Dockerfile.frontend")) {
        Write-Error "Dockerfile.frontend not found in current directory."
        exit 1
    }
    
    # Create fly configuration
    Write-Status "Creating Fly.io configuration..."
    
    $frontendConfig = @"
# Fly.io Configuration for SmartResume AI Frontend Service
app = "$AppName"
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
"@
    
    $frontendConfig | Set-Content $ConfigFile
    Write-Success "Created $ConfigFile"
    
    # Check if app exists
    Write-Status "Checking if app exists..."
    $appExists = fly apps list | Select-String $AppName
    
    if (-not $appExists) {
        Write-Status "Creating new app: $AppName"
        fly apps create $AppName
        Write-Success "Created app: $AppName"
    } else {
        Write-Success "App $AppName already exists"
    }
    
    # Determine backend URL
    Write-Status "Determining backend URL..."
    $backendExists = fly apps list | Select-String $BackendAppName
    
    if ($backendExists) {
        $BackendUrl = "https://$BackendAppName.fly.dev"
        Write-Success "Found backend app: $BackendUrl"
    } else {
        Write-Warning "Backend app $BackendAppName not found."
        $BackendUrl = Read-Host "Enter backend URL (e.g., https://smartresume-backend-prod.fly.dev)"
        
        if (-not $BackendUrl) {
            Write-Error "Backend URL is required for frontend deployment."
            exit 1
        }
    }
    
    Write-Status "Using backend URL: $BackendUrl"
    
    # Set environment secrets
    Write-Status "Setting up environment secrets..."
    Write-Host ""
    Write-Host "Please provide the following environment variables:"
    Write-Host "You can skip any that are already set by pressing Enter."
    Write-Host ""
    
    $ApiUrl = Read-Host "VITE_API_URL (default: $BackendUrl)"
    if (-not $ApiUrl) { $ApiUrl = $BackendUrl }
    fly secrets set "VITE_API_URL=$ApiUrl" -a $AppName
    
    $SupabaseUrl = Read-Host "VITE_SUPABASE_URL (Supabase project URL)"
    if ($SupabaseUrl) {
        fly secrets set "VITE_SUPABASE_URL=$SupabaseUrl" -a $AppName
    }
    
    $SupabaseAnonKey = Read-Host "VITE_SUPABASE_ANON_KEY (Supabase anonymous key)"
    if ($SupabaseAnonKey) {
        fly secrets set "VITE_SUPABASE_ANON_KEY=$SupabaseAnonKey" -a $AppName
    }
    
    Write-Success "Environment secrets configured"
    
    # Deploy the application
    Write-Status "Deploying frontend application..."
    
    try {
        fly deploy -c $ConfigFile
        Write-Success "Frontend deployment completed successfully!"
        
        # Show app status
        Write-Host ""
        Write-Status "Application status:"
        fly status -a $AppName
        
        # Test frontend
        Write-Host ""
        Write-Status "Testing frontend..."
        Start-Sleep -Seconds 10
        
        $AppUrl = "https://$AppName.fly.dev"
        try {
            $response = Invoke-WebRequest -Uri $AppUrl -Method Get -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                Write-Success "Frontend is accessible: $AppUrl"
            }
        }
        catch {
            Write-Warning "Frontend test failed. App might still be starting up."
            Write-Status "You can check logs with: fly logs -a $AppName"
        }
        
        Write-Host ""
        Write-Success "Frontend service is available at: $AppUrl"
        
        return $true
    }
    catch {
        Write-Error "Deployment failed!"
        Write-Status "Check logs with: fly logs -a $AppName"
        return $false
    }
}

# Main execution
function Main {
    Write-Host "==============================================" -ForegroundColor $Colors.Blue
    Write-Host "SmartResume AI Deployment Script (PowerShell)" -ForegroundColor $Colors.Blue
    Write-Host "==============================================" -ForegroundColor $Colors.Blue
    Write-Host ""
    
    if ($Help) {
        Show-Usage
        return
    }
    
    # Validate conflicting options
    if ($BackendOnly -and $FrontendOnly) {
        Write-Error "Cannot specify both -BackendOnly and -FrontendOnly"
        exit 1
    }
    
    Write-Status "App suffix: $AppSuffix"
    
    if ($BackendOnly) {
        Write-Status "Mode: Backend only"
    } elseif ($FrontendOnly) {
        Write-Status "Mode: Frontend only"
    } else {
        Write-Status "Mode: Full deployment (backend + frontend)"
    }
    
    Write-Host ""
    
    # Check prerequisites
    Test-Prerequisites
    
    # Initialize deployment flags
    $BackendDeployed = $false
    $FrontendDeployed = $false
    
    # Deploy services based on options
    if (-not $FrontendOnly) {
        $BackendDeployed = Deploy-Backend -Suffix $AppSuffix
        if (-not $BackendDeployed) {
            Write-Error "Backend deployment failed. Stopping."
            exit 1
        }
    }
    
    if (-not $BackendOnly) {
        $FrontendDeployed = Deploy-Frontend -Suffix $AppSuffix
        if (-not $FrontendDeployed) {
            Write-Error "Frontend deployment failed. Stopping."
            exit 1
        }
    }
    
    # Show summary
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor $Colors.Green
    Write-Host "DEPLOYMENT SUMMARY" -ForegroundColor $Colors.Green
    Write-Host "==========================================" -ForegroundColor $Colors.Green
    
    if ($BackendDeployed) {
        Write-Host "✓ Backend Service:" -ForegroundColor $Colors.Green
        Write-Host "  App Name: smartresume-backend-$AppSuffix"
        Write-Host "  URL: https://smartresume-backend-$AppSuffix.fly.dev"
        Write-Host "  Health: https://smartresume-backend-$AppSuffix.fly.dev/api/v1/health"
    }
    
    if ($FrontendDeployed) {
        Write-Host "✓ Frontend Service:" -ForegroundColor $Colors.Green
        Write-Host "  App Name: smartresume-frontend-$AppSuffix"
        Write-Host "  URL: https://smartresume-frontend-$AppSuffix.fly.dev"
    }
    
    Write-Host ""
    Write-Host "Useful Commands:"
    
    if ($BackendDeployed) {
        Write-Host "  Backend logs:  fly logs -a smartresume-backend-$AppSuffix"
        Write-Host "  Backend scale: fly scale memory 1024 -a smartresume-backend-$AppSuffix"
    }
    
    if ($FrontendDeployed) {
        Write-Host "  Frontend logs: fly logs -a smartresume-frontend-$AppSuffix"
        Write-Host "  Frontend scale: fly scale memory 512 -a smartresume-frontend-$AppSuffix"
    }
    
    Write-Host ""
    Write-Success "Deployment process completed!"
}

# Add System.Web assembly for password generation
Add-Type -AssemblyName System.Web

# Run main function
Main