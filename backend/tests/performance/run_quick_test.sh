#!/bin/bash

# Quick performance test script for SmartResume AI Resume Analyzer
# This script runs a basic load test to validate the 30-second requirement

echo "========================================"
echo "SmartResume Performance Quick Test"
echo "========================================"

# Check if the application is running
echo "Checking if application is running..."
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ Application is running"
else
    echo "❌ Application is not running at http://localhost:8000"
    echo "Please start the application first:"
    echo "  cd backend && python -m app.main"
    exit 1
fi

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo "❌ Locust is not installed"
    echo "Please install it: pip install locust"
    exit 1
fi

echo "✅ Locust is available"

# Create results directory
mkdir -p results

# Run quick performance test
echo ""
echo "Running quick performance test..."
echo "- 25 concurrent users"
echo "- 5-minute duration"
echo "- Testing 30-second requirement"
echo ""

locust -f locustfile.py \
    --host http://localhost:8000 \
    --users 25 \
    --spawn-rate 5 \
    --run-time 5m \
    --headless \
    --print-stats \
    --html results/quick_test_report.html \
    --csv results/quick_test

echo ""
echo "========================================"
echo "Quick test completed!"
echo "Results saved to:"
echo "  - HTML Report: results/quick_test_report.html"
echo "  - CSV Data: results/quick_test_*.csv"
echo ""
echo "For comprehensive validation, run:"
echo "  python validate_requirements.py"
echo "========================================"