# Web Platform Compatible: Full-Stack with Runtime Model Downloads
# No shell commands required - works with Fly.io web dashboard

FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
RUN apk add --no-cache python3 make g++
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    TORCH_CUDA_ARCH_LIST="" \
    FORCE_CUDA=0

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl nodejs npm poppler-utils tesseract-ocr tesseract-ocr-eng \
    libmagic1 build-essential gcc g++ libffi-dev libssl-dev \
    && npm install -g serve \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

RUN groupadd -r --gid 1000 appuser && \
    useradd -r --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Install ALL Python dependencies from requirements.txt
COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --only-binary=all -r requirements.txt && \
    pip cache purge

# Copy application files
COPY --chown=appuser:appuser backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

# Create Python script for model downloads
RUN cat > /app/download_models.py << 'EOF'
#!/usr/bin/env python3
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_directory(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def download_models():
    logger.info("Checking for ML models...")
    
    # Create model directories
    ensure_directory("/app/models/spacy")
    ensure_directory("/app/models/transformers")
    
    # Download spaCy model if not exists
    try:
        import spacy
        if not os.path.exists("/app/models/spacy/en_core_web_sm"):
            logger.info("Downloading spaCy model...")
            spacy.cli.download("en_core_web_sm")
        else:
            logger.info("spaCy model already cached")
    except Exception as e:
        logger.warning(f"spaCy model download failed: {e}")
    
    # Initialize sentence transformer (downloads if needed)
    try:
        from sentence_transformers import SentenceTransformer
        cache_dir = "/app/models/sentence_transformers"
        ensure_directory(cache_dir)
        if not os.path.exists(f"{cache_dir}/sentence-transformers_all-MiniLM-L6-v2"):
            logger.info("Downloading sentence transformer...")
            SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", cache_folder=cache_dir)
        else:
            logger.info("Sentence transformer already cached")
    except Exception as e:
        logger.warning(f"Sentence transformer download failed: {e}")
    
    logger.info("Model initialization complete")

if __name__ == "__main__":
    download_models()
EOF

# Create startup script
RUN cat > /app/start.sh << 'EOF'
#!/bin/bash
echo "=== Resume Insight AI Starting ==="
python3 /app/download_models.py
serve -s /app/frontend/dist -l 3000 &
cd /app/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
EOF

RUN chmod +x /app/download_models.py /app/start.sh && \
    mkdir -p /app/logs /app/temp /app/uploads /app/models && \
    chown -R appuser:appuser /app

USER appuser
EXPOSE 8000 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["/app/start.sh"]