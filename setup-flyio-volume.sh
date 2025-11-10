#!/bin/bash
# Setup script for Fly.io volume storage

echo "Setting up Fly.io volume for ML models..."

# Create volume for ML model storage (10GB should be enough)
echo "Creating volume for ML models..."
flyctl volumes create ml_models_vol --size 10 --region iad -a resume-insight-ai-88

echo "Volume created successfully!"
echo ""
echo "Now you can deploy with:"
echo "flyctl deploy -a resume-insight-ai-88"
echo ""
echo "The application will:"
echo "1. Build Docker image under 8GB (no models included)"
echo "2. Download ML models at startup to persistent volume"
echo "3. Cache models for future restarts"
echo "4. Provide full ML functionality"