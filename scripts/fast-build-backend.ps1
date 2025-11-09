# Fast Docker build script for backend with advanced caching
# Uses Docker BuildKit for maximum performance

Write-Host "🚀 Starting optimized backend build with BuildKit..." -ForegroundColor Green

# Enable Docker BuildKit for faster builds
$env:DOCKER_BUILDKIT = "1"
$env:BUILDKIT_PROGRESS = "plain"

# Build with cache mounts and parallel processing
docker build `
    --file Dockerfile.backend `
    --tag smartresume-backend:latest `
    --build-arg BUILDKIT_INLINE_CACHE=1 `
    --progress=plain `
    .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Backend build completed successfully!" -ForegroundColor Green
    Write-Host "📦 Image: smartresume-backend:latest" -ForegroundColor Cyan
} else {
    Write-Host "❌ Backend build failed!" -ForegroundColor Red
    exit 1
}