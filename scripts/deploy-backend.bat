@echo off
REM SmartResume AI Backend Deployment Script for Fly.io (Windows)
REM This script automates the deployment of the FastAPI backend service

setlocal enabledelayedexpansion

REM Configuration
set DEFAULT_APP_SUFFIX=prod
set CONFIG_FILE=fly-backend.toml

REM Colors (if supported)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

echo ==========================================
echo SmartResume AI Backend Deployment Script
echo ==========================================
echo.

REM Check if help is requested
if "%1"=="-h" goto :show_usage
if "%1"=="--help" goto :show_usage

REM Check prerequisites
echo %BLUE%[INFO]%NC% Checking prerequisites...

REM Check if fly command exists
fly --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%NC% Fly.io CLI not found. Please install it from https://fly.io/docs/getting-started/installing-flyctl/
    exit /b 1
)

REM Check if logged in to Fly.io
fly auth whoami >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%NC% Not logged in to Fly.io. Please run 'fly auth login' first.
    exit /b 1
)

REM Check if Dockerfile exists
if not exist "Dockerfile.backend" (
    echo %RED%[ERROR]%NC% Dockerfile.backend not found in current directory.
    exit /b 1
)

echo %GREEN%[SUCCESS]%NC% Prerequisites check passed

REM Get app suffix
if "%1"=="" (
    set /p APP_SUFFIX="Enter app suffix (default: %DEFAULT_APP_SUFFIX%): "
    if "!APP_SUFFIX!"=="" set APP_SUFFIX=%DEFAULT_APP_SUFFIX%
) else (
    set APP_SUFFIX=%1
)

set APP_NAME=smartresume-backend-!APP_SUFFIX!
echo %BLUE%[INFO]%NC% Using app name: !APP_NAME!

REM Create fly configuration
echo %BLUE%[INFO]%NC% Creating Fly.io configuration...

if not exist "%CONFIG_FILE%" (
    if not exist "fly.toml" (
        echo %RED%[ERROR]%NC% fly.toml template not found. Please ensure the template exists.
        exit /b 1
    )
    
    echo %BLUE%[INFO]%NC% Copying fly.toml to %CONFIG_FILE%...
    copy fly.toml "%CONFIG_FILE%" >nul
)

REM Update app name in config file (basic replacement)
powershell -Command "(Get-Content '%CONFIG_FILE%') -replace 'smartresume-backend-\[YOUR-SUFFIX\]', '!APP_NAME!' | Set-Content '%CONFIG_FILE%'"
echo %GREEN%[SUCCESS]%NC% Updated app name in %CONFIG_FILE%

REM Check if app exists
echo %BLUE%[INFO]%NC% Checking if app exists...
fly apps list | findstr "!APP_NAME!" >nul
if errorlevel 1 (
    echo %BLUE%[INFO]%NC% Creating new app: !APP_NAME!
    fly apps create "!APP_NAME!"
    echo %GREEN%[SUCCESS]%NC% Created app: !APP_NAME!
) else (
    echo %GREEN%[SUCCESS]%NC% App !APP_NAME! already exists
)

REM Set environment secrets
echo %BLUE%[INFO]%NC% Setting up environment secrets...
echo.
echo Please provide the following environment variables:
echo You can skip any that are already set by pressing Enter.
echo.

set /p DATABASE_URL="DATABASE_URL (Supabase connection string): "
if not "!DATABASE_URL!"=="" (
    fly secrets set DATABASE_URL="!DATABASE_URL!" -a "!APP_NAME!"
)

set /p GOOGLE_API_KEY="GOOGLE_API_KEY (Gemini API key): "
if not "!GOOGLE_API_KEY!"=="" (
    fly secrets set GOOGLE_API_KEY="!GOOGLE_API_KEY!" -a "!APP_NAME!"
)

set /p JWT_SECRET="JWT_SECRET (or press Enter to generate): "
if "!JWT_SECRET!"=="" (
    REM Generate a simple JWT secret using PowerShell
    for /f %%i in ('powershell -Command "[System.Web.Security.Membership]::GeneratePassword(32, 8)"') do set JWT_SECRET=%%i
    echo %BLUE%[INFO]%NC% Generated JWT_SECRET: !JWT_SECRET!
)
fly secrets set JWT_SECRET="!JWT_SECRET!" -a "!APP_NAME!"

set /p SUPABASE_URL="SUPABASE_URL (Supabase project URL): "
if not "!SUPABASE_URL!"=="" (
    fly secrets set SUPABASE_URL="!SUPABASE_URL!" -a "!APP_NAME!"
)

set /p SUPABASE_SERVICE_KEY="SUPABASE_SERVICE_KEY (Supabase service role key): "
if not "!SUPABASE_SERVICE_KEY!"=="" (
    fly secrets set SUPABASE_SERVICE_KEY="!SUPABASE_SERVICE_KEY!" -a "!APP_NAME!"
)

echo %GREEN%[SUCCESS]%NC% Environment secrets configured

REM Deploy the application
echo %BLUE%[INFO]%NC% Deploying backend application...

fly deploy -c "%CONFIG_FILE%"
if errorlevel 1 (
    echo %RED%[ERROR]%NC% Deployment failed!
    echo %BLUE%[INFO]%NC% Check logs with: fly logs -a !APP_NAME!
    exit /b 1
)

echo %GREEN%[SUCCESS]%NC% Backend deployment completed successfully!

REM Show app status
echo.
echo %BLUE%[INFO]%NC% Application status:
fly status -a "!APP_NAME!"

REM Test health endpoint
echo.
echo %BLUE%[INFO]%NC% Testing health endpoint...
timeout /t 10 /nobreak >nul

set APP_URL=https://!APP_NAME!.fly.dev
curl -f "!APP_URL!/api/v1/health" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[WARNING]%NC% Health check failed. App might still be starting up.
    echo %BLUE%[INFO]%NC% You can check logs with: fly logs -a !APP_NAME!
) else (
    echo %GREEN%[SUCCESS]%NC% Health check passed: !APP_URL!/api/v1/health
)

echo.
echo %GREEN%[SUCCESS]%NC% Backend service is available at: !APP_URL!
echo %BLUE%[INFO]%NC% Use this URL as VITE_API_URL when deploying the frontend

echo.
echo %GREEN%[SUCCESS]%NC% Backend deployment process completed!
echo %BLUE%[INFO]%NC% Next steps:
echo   1. Test the backend API at !APP_URL!
echo   2. Deploy the frontend using: scripts\deploy-frontend.bat
echo   3. Monitor logs with: fly logs -a !APP_NAME!

goto :end

:show_usage
echo Usage: %0 [app-suffix]
echo.
echo Options:
echo   app-suffix    Suffix for the app name (default: %DEFAULT_APP_SUFFIX%)
echo.
echo Examples:
echo   %0              # Creates smartresume-backend-prod
echo   %0 staging      # Creates smartresume-backend-staging
echo   %0 dev          # Creates smartresume-backend-dev
echo.
echo Environment Variables:
echo   The script will prompt for required environment variables:
echo   - DATABASE_URL
echo   - GOOGLE_API_KEY
echo   - JWT_SECRET (auto-generated if not provided)
echo   - SUPABASE_URL
echo   - SUPABASE_SERVICE_KEY

:end
endlocal