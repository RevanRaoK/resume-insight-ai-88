@echo off
REM Quick performance test script for SmartResume AI Resume Analyzer
REM This script runs a basic load test to validate the 30-second requirement

echo ========================================
echo SmartResume Performance Quick Test
echo ========================================

REM Check if the application is running
echo Checking if application is running...
curl -s http://localhost:8000/api/v1/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Application is running
) else (
    echo ❌ Application is not running at http://localhost:8000
    echo Please start the application first:
    echo   cd backend ^&^& python -m app.main
    exit /b 1
)

REM Check if locust is installed
locust --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Locust is available
) else (
    echo ❌ Locust is not installed
    echo Please install it: pip install locust
    exit /b 1
)

REM Create results directory
if not exist results mkdir results

REM Run quick performance test
echo.
echo Running quick performance test...
echo - 25 concurrent users
echo - 5-minute duration
echo - Testing 30-second requirement
echo.

locust -f locustfile.py --host http://localhost:8000 --users 25 --spawn-rate 5 --run-time 5m --headless --print-stats --html results/quick_test_report.html --csv results/quick_test

echo.
echo ========================================
echo Quick test completed!
echo Results saved to:
echo   - HTML Report: results/quick_test_report.html
echo   - CSV Data: results/quick_test_*.csv
echo.
echo For comprehensive validation, run:
echo   python validate_requirements.py
echo ========================================