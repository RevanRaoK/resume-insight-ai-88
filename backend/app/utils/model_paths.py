"""
Model path configuration for volume storage
"""
import os
from pathlib import Path

# Base model directory (mounted volume)
MODEL_BASE_DIR = Path("/app/models")

# Model-specific paths
SPACY_MODEL_DIR = MODEL_BASE_DIR / "spacy"
TRANSFORMERS_CACHE_DIR = MODEL_BASE_DIR / "transformers"
HUGGINGFACE_CACHE_DIR = MODEL_BASE_DIR / "huggingface"
SENTENCE_TRANSFORMERS_CACHE_DIR = MODEL_BASE_DIR / "sentence_transformers"

# Environment variables for model caching
def setup_model_environment():
    """Setup environment variables for model caching"""
    os.environ["SPACY_DATA_DIR"] = str(SPACY_MODEL_DIR)
    os.environ["TRANSFORMERS_CACHE"] = str(TRANSFORMERS_CACHE_DIR)
    os.environ["HF_HOME"] = str(HUGGINGFACE_CACHE_DIR)
    
    # Create directories if they don't exist
    for path in [SPACY_MODEL_DIR, TRANSFORMERS_CACHE_DIR, 
                 HUGGINGFACE_CACHE_DIR, SENTENCE_TRANSFORMERS_CACHE_DIR]:
        path.mkdir(parents=True, exist_ok=True)

# Call setup on import
setup_model_environment()