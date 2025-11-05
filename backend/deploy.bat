@echo off
REM SmartResume AI Resume Analyzer Deployment Script for Windows
REM This script automates the deployment process for production environments

setlocal enabledelayedexpansion

REM Configuration
set APP_NAME=smartresume-ai
set DOCKER_COMPOSE_FILE=docker-compose.yml
set BACKUP_DIR=.\backups
set LOG_FILE=.\logs\deployment.log

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Logging function
set "timestamp=%date% %time%"
echo [%timestamp%] Starting deployment of %APP_NAME%... >> %LOG_FILE%

REM Check prerequisites
echo Checking prerequisites...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not in PATH
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Compose is not installed or not in PATH
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found
    if exist .env.production (
        echo Copying .env.production to .env...
        copy .env.production .env
        echo Please edit .env file with your production configuration
        pause
    ) else (
        echo ERROR: .env.production template not found
        exit /b 1
    )
)

REM Create necessary directories
echo Creating necessary directories...
if not exist logs mkdir logs
if not exist temp mkdir temp
if not exist nginx\ssl mkdir nginx\ssl
if not exist monitoring mkdir monitoring
if not exist %BACKUP_DIR% mkdir %BACKUP_DIR%

REM Backup current deployment
echo Creating backup of current deployment...
set backup_timestamp=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set backup_timestamp=%backup_timestamp: =0%
set BACKUP_PATH=%BACKUP_DIR%\backup_%backup_timestamp%
mkdir %BACKUP_PATH%

if exist .env copy .env %BACKUP_PATH%\
if exist %DOCKER_COMPOSE_FILE% copy %DOCKER_COMPOSE_FILE% %BACKUP_PATH%\
if exist logs xcopy logs %BACKUP_PATH%\logs\ /E /I /Q

echo Backup created at %BACKUP_PATH%

REM Build Docker images
echo Building Docker images...
docker-compose -f %DOCKER_COMPOSE_FILE% build --no-cache
if errorlevel 1 (
    echo ERROR: Failed to build Docker images
    exit /b 1
)

REM Deploy application
echo Deploying application...
echo Stopping existing containers...
docker-compose -f %DOCKER_COMPOSE_FILE% down --remove-orphans

echo Starting new containers...
docker-compose -f %DOCKER_COMPOSE_FILE% up -d
if errorlevel 1 (
    echo ERROR: Failed to start containers
    exit /b 1
)

REM Health check
echo Performing health check...
timeout /t 30 /nobreak >nul

set /a retry_count=0
set /a max_retries=10

:health_check_loop
curl -f http://localhost:8000/api/v1/health >nul 2>&1
if not errorlevel 1 (
    echo SUCCESS: Health check passed
    goto health_check_success
)

set /a retry_count+=1
if %retry_count% geq %max_retries% (
    echo ERROR: Health check failed after %max_retries% attempts
    exit /b 1
)

echo Health check attempt %retry_count%/%max_retries% failed. Retrying in 10 seconds...
timeout /t 10 /nobreak >nul
goto health_check_loop

:health_check_success

REM Cleanup
echo Cleaning up old Docker images and containers...
docker image prune -f
docker container prune -f

REM Show status
echo.
echo ==================== 
echo Deployment Status:
echo ==================== 
echo.
echo Running Containers:
docker-compose -f %DOCKER_COMPOSE_FILE% ps
echo.
echo Service URLs:
echo - API: http://localhost:8000
echo - Health Check: http://localhost:8000/api/v1/health
echo - API Documentation: http://localhost:8000/docs
echo.
echo Useful Commands:
echo - View logs: docker-compose logs -f
echo - Stop services: docker-compose down
echo - Restart services: docker-compose restart
echo.

echo SUCCESS: Deployment completed successfully!
echo Check the application at: http://localhost:8000/api/v1/health

REM Handle script arguments
if "%1"=="stop" (
    echo Stopping %APP_NAME%...
    docker-compose -f %DOCKER_COMPOSE_FILE% down
    echo Application stopped.
    goto end
)

if "%1"=="restart" (
    echo Restarting %APP_NAME%...
    docker-compose -f %DOCKER_COMPOSE_FILE% restart
    echo Application restarted.
    goto end
)

if "%1"=="logs" (
    docker-compose -f %DOCKER_COMPOSE_FILE% logs -f
    goto end
)

if "%1"=="status" (
    docker-compose -f %DOCKER_COMPOSE_FILE% ps
    goto end
)

:end
endlocal