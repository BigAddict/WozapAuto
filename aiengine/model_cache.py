"""
Global model caching for SentenceTransformer to improve performance.
This singleton pattern ensures the model is loaded only once and reused.
"""
import logging
from sentence_transformers import SentenceTransformer
from typing import Optional

logger = logging.getLogger("aiengine.model_cache")


class ModelCache:
    """
    Singleton class for caching SentenceTransformer model globally.
    This eliminates the 4-5 second loading time on each request.
    """
    _instance: Optional['ModelCache'] = None
    _model: Optional[SentenceTransformer] = None
    _model_name: str = 'all-MiniLM-L6-v2'
    _embedding_dimensions: int = 384
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_model(self) -> SentenceTransformer:
        """
        Get the cached SentenceTransformer model.
        Loads the model only on first access.
        
        Returns:
            SentenceTransformer: The cached model instance
        """
        if self._model is None:
            logger.info(f"Loading SentenceTransformer model: {self._model_name} (first time only)")
            try:
                self._model = SentenceTransformer(self._model_name)
                logger.info(f"Successfully loaded and cached model: {self._model_name}")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer model: {e}")
                # Try fallback models
                fallback_models = [
                    'paraphrase-MiniLM-L6-v2',
                    'all-MiniLM-L12-v2',
                    'distilbert-base-nli-mean-tokens'
                ]
                
                for fallback in fallback_models:
                    try:
                        logger.info(f"Trying fallback model: {fallback}")
                        self._model = SentenceTransformer(fallback)
                        self._model_name = fallback
                        logger.info(f"Successfully loaded fallback model: {fallback}")
                        break
                    except Exception as fallback_error:
                        logger.warning(f"Fallback model {fallback} failed: {fallback_error}")
                        continue
                
                if self._model is None:
                    raise RuntimeError("Failed to load any SentenceTransformer model")
        
        return self._model
    
    def get_embedding_dimensions(self) -> int:
        """Get the embedding dimensions for the current model."""
        return self._embedding_dimensions
    
    def get_model_name(self) -> str:
        """Get the name of the currently loaded model."""
        return self._model_name
    
    def is_loaded(self) -> bool:
        """Check if the model is already loaded."""
        return self._model is not None
    
    def clear_cache(self):
        """
        Clear the model cache (useful for testing or memory management).
        Next call to get_model() will reload the model.
        """
        logger.info("Clearing model cache")
        self._model = None
        self._model_name = 'all-MiniLM-L6-v2'
        self._embedding_dimensions = 384


# Global instance for easy access
model_cache = ModelCache()