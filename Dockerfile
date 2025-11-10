# Optimized Full-Stack Dockerfile for Fly.io (Frontend + Backend + ML)
# Multi-stage build with all features under 8GB limit

# Stage 1: Frontend Builder
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install build dependencies
RUN apk add --no-cache python3 make g++

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm ci --ignore-scripts

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend with ML - Optimized Production
FROM python:3.11-slim AS production

# Set build environment variables for optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    TORCH_CUDA_ARCH_LIST="" \
    FORCE_CUDA=0 \
    TRANSFORMERS_CACHE=/tmp/transformers_cache \
    HF_HOME=/tmp/hf_cache

# Install system dependencies (Python + Node.js for serving)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python runtime dependencies
    curl \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    libmagic1 \
    build-essential \
    # Node.js for serving frontend
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Install serve for frontend hosting
RUN npm install -g serve

# Create non-root user
RUN groupadd -r --gid 1000 appuser && \
    useradd -r --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies with optimization
COPY backend/requirements.minimal.txt ./requirements.txt

# Install dependencies in optimized order (smallest to largest)
RUN pip install --upgrade pip setuptools wheel && \
    # Install lightweight dependencies first
    pip install --no-cache-dir --only-binary=all \
        fastapi==0.104.1 \
        uvicorn[standard]==0.24.0 \
        python-multipart==0.0.6 \
        pydantic==2.5.0 \
        pydantic-settings==2.1.0 \
        PyJWT==2.8.0 \
        python-jose[cryptography]==3.3.0 \
        asyncpg==0.29.0 \
        supabase==2.3.0 \
        structlog==23.2.0 \
        python-json-logger==2.0.7 \
        psutil==5.9.6 \
        google-generativeai==0.3.2 \
        pdfplumber==0.10.0 \
        python-docx==1.1.0 \
        chardet==5.2.0 && \
    # Install numpy and scikit-learn (medium size)
    pip install --no-cache-dir --only-binary=all \
        numpy==1.24.3 \
        scikit-learn==1.3.2 && \
    # Install PyTorch CPU-only (optimized)
    pip install --no-cache-dir --only-binary=all \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.1.0+cpu && \
    # Install transformers and sentence-transformers
    pip install --no-cache-dir --only-binary=all \
        transformers==4.35.0 \
        sentence-transformers==2.2.2 && \
    # Install spaCy (without models initially)
    pip install --no-cache-dir --only-binary=all \
        spacy==3.7.2 && \
    # Download only the small English model for spaCy
    python -m spacy download en_core_web_sm && \
    # Clean up pip cache and temporary files
    pip cache purge && \
    rm -rf /tmp/* /var/tmp/* && \
    # Remove unnecessary files from installed packages
    find /usr/local/lib/python3.11/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.11/site-packages -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy backend application
COPY --chown=appuser:appuser backend/ ./backend/

# Copy built frontend from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

# Create directories with proper permissions
RUN mkdir -p /app/logs /app/temp /app/uploads && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Create startup script for both frontend and backend
COPY --chown=appuser:appuser <<EOF /app/start.sh
#!/bin/bash
# Start frontend server in background
serve -s /app/frontend/dist -l 3000 &
# Start backend server
cd /app/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
EOF

RUN chmod +x /app/start.sh

# Switch to non-root user
USER appuser

# Expose ports (backend on 8000, frontend on 3000)
EXPOSE 8000 3000

# Health check for backend
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start both services
CMD ["/app/start.sh"]