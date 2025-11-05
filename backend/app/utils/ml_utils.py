"""
ML model loading and caching utilities for NLU system
"""
import asyncio
import threading
from typing import Optional, Dict, Any
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from sentence_transformers import SentenceTransformer
import torch
from app.utils.logger import get_logger
from app.core.exceptions import NLUProcessingError

logger = get_logger(__name__)


class ModelCache:
    """
    Singleton class for loading and caching ML models at startup.
    Provides memory-efficient model caching to minimize latency.
    """
    
    _instance: Optional['ModelCache'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'ModelCache':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self._models: Dict[str, Any] = {}
            self._tokenizers: Dict[str, Any] = {}
            self._pipelines: Dict[str, Any] = {}
            self._model_health: Dict[str, bool] = {}
            self._initialized = True
    
    async def load_models_at_startup(self) -> None:
        """
        Load all ML models into memory during application startup.
        Implements error handling and fallback mechanisms.
        """
        logger.info("Starting ML model loading process")
        
        try:
            # Load NER model and tokenizer
            await self._load_ner_model()
            
            # Load sentence transformer model
            await self._load_sentence_transformer()
            
            logger.info("All ML models loaded successfully", 
                       models_loaded=list(self._models.keys()))
            
        except Exception as e:
            logger.error("Failed to load ML models", error=str(e))
            raise NLUProcessingError(f"Model loading failed: {str(e)}")
    
    async def _load_ner_model(self) -> None:
        """Load the NER model for resume entity extraction"""
        try:
            model_name = "yashpwr/resume-ner-bert-v2"
            logger.info("Loading NER model", model_name=model_name)
            
            # Run model loading in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Load tokenizer
            tokenizer = await loop.run_in_executor(
                None, 
                AutoTokenizer.from_pretrained, 
                model_name
            )
            
            # Load model
            model = await loop.run_in_executor(
                None,
                AutoModelForTokenClassification.from_pretrained,
                model_name
            )
            
            # Create pipeline
            ner_pipeline = await loop.run_in_executor(
                None,
                pipeline,
                "ner",
                model=model,
                tokenizer=tokenizer,
                aggregation_strategy="simple",
                device=-1  # Use CPU for better compatibility
            )
            
            self._models["ner_model"] = model
            self._tokenizers["ner_tokenizer"] = tokenizer
            self._pipelines["ner_pipeline"] = ner_pipeline
            self._model_health["ner"] = True
            
            logger.info("NER model loaded successfully")
            
        except Exception as e:
            logger.error("Failed to load NER model", error=str(e))
            self._model_health["ner"] = False
            raise
    
    async def _load_sentence_transformer(self) -> None:
        """Load the sentence transformer model for semantic analysis"""
        try:
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            logger.info("Loading sentence transformer model", model_name=model_name)
            
            # Run model loading in thread pool
            loop = asyncio.get_event_loop()
            
            sentence_model = await loop.run_in_executor(
                None,
                SentenceTransformer,
                model_name
            )
            
            self._models["sentence_transformer"] = sentence_model
            self._model_health["sentence_transformer"] = True
            
            logger.info("Sentence transformer model loaded successfully")
            
        except Exception as e:
            logger.error("Failed to load sentence transformer model", error=str(e))
            self._model_health["sentence_transformer"] = False
            raise
    
    def get_ner_pipeline(self) -> Optional[Any]:
        """Get the NER pipeline for entity extraction"""
        if not self._model_health.get("ner", False):
            logger.warning("NER model is not healthy")
            return None
        return self._pipelines.get("ner_pipeline")
    
    def get_sentence_transformer(self) -> Optional[SentenceTransformer]:
        """Get the sentence transformer model for embeddings"""
        if not self._model_health.get("sentence_transformer", False):
            logger.warning("Sentence transformer model is not healthy")
            return None
        return self._models.get("sentence_transformer")
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Perform health checks on all loaded models.
        Returns dict with model names and their health status.
        """
        health_status = {}
        
        # Check NER model health
        try:
            ner_pipeline = self.get_ner_pipeline()
            if ner_pipeline is not None:
                # Test with simple text
                test_result = ner_pipeline("John Doe is a software engineer")
                health_status["ner"] = isinstance(test_result, list)
            else:
                health_status["ner"] = False
        except Exception as e:
            logger.error("NER model health check failed", error=str(e))
            health_status["ner"] = False
            self._model_health["ner"] = False
        
        # Check sentence transformer health
        try:
            sentence_model = self.get_sentence_transformer()
            if sentence_model is not None:
                # Test with simple text
                test_embedding = sentence_model.encode("test text")
                health_status["sentence_transformer"] = len(test_embedding) > 0
            else:
                health_status["sentence_transformer"] = False
        except Exception as e:
            logger.error("Sentence transformer health check failed", error=str(e))
            health_status["sentence_transformer"] = False
            self._model_health["sentence_transformer"] = False
        
        return health_status
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        return {
            "loaded_models": list(self._models.keys()),
            "model_health": self._model_health.copy(),
            "memory_usage": self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> Dict[str, str]:
        """Get approximate memory usage of loaded models"""
        memory_info = {}
        
        for model_name, model in self._models.items():
            try:
                if hasattr(model, 'get_memory_footprint'):
                    memory_info[model_name] = f"{model.get_memory_footprint() / 1024 / 1024:.2f} MB"
                else:
                    # Rough estimate based on parameters
                    if hasattr(model, 'num_parameters'):
                        params = model.num_parameters()
                        memory_info[model_name] = f"~{params * 4 / 1024 / 1024:.2f} MB"
                    else:
                        memory_info[model_name] = "Unknown"
            except Exception:
                memory_info[model_name] = "Unknown"
        
        return memory_info


# Global instance
model_cache = ModelCache()