#!/bin/bash
# Fast Docker build script for backend with advanced caching
# Uses Docker BuildKit for maximum performance

echo "🚀 Starting optimized backend build with BuildKit..."

# Enable Docker BuildKit for faster builds
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

# Build with cache mounts and parallel processing
docker build \
    --file Dockerfile.backend \
    --tag smartresume-backend:latest \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --progress=plain \
    .

if [ $? -eq 0 ]; then
    echo "✅ Backend build completed successfully!"
    echo "📦 Image: smartresume-backend:latest"
else
    echo "❌ Backend build failed!"
    exit 1
fi