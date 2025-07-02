"""
Generic embedder for unified text embedding across different model types.
"""

import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np

from ..factory import ModelFactory
from ...config.config import Config


class GenericEmbedder:
    """
    Universal text embedder that works with any embedding model.
    
    Supports:
    - HuggingFace embedding models
    - OpenAI embedding models (via API)
    - Custom embedding models
    """
    
    def __init__(self, model_name: Optional[str] = None, provider: Optional[str] = None, **kwargs):
        """
        Initialize the embedder.
        
        Args:
            model_name: Name of the embedding model. If None, uses default from config
            provider: Provider for the model (e.g., 'openai', 'huggingface')
            **kwargs: Additional arguments for model initialization
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = Config()
        
        if model_name is None:
            # Get default from configuration
            model_name = self.config.get_default_embedding_model()
        
        self.model_name = model_name
        self.provider = provider
        
        # Auto-detect model type and create appropriate wrapper
        try:
            self.model_wrapper = ModelFactory.create(model_name, task="embeddings", provider=provider, **kwargs)
        except Exception as e:
            self.logger.warning(f"Failed to create with auto-detection: {e}")
            # Fallback to explicit embedding creation
            self.model_wrapper = ModelFactory.create_embedder(model_name, **kwargs)
            
        self.logger.info(f"Initialized embedder with {self.model_wrapper.get_model_type()} model: {model_name}")
    
    def embed(self, text: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Generate embeddings for text.
        
        Args:
            text: Single text or list of texts to embed
            
        Returns:
            Embeddings as numpy array(s)
        """
        result = self.model_wrapper.predict(text)
        
        if isinstance(text, str):
            return self._extract_single_embedding(result)
        else:
            return self._extract_batch_embeddings(result)
    
    def embed_batch(self, texts: List[str], batch_size: int = 8) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            batch_size: Size of processing batches
            
        Returns:
            List of embedding arrays
        """
        if hasattr(self.model_wrapper, 'batch_predict'):
            result = self.model_wrapper.batch_predict(texts, batch_size=batch_size)
            return self._extract_batch_embeddings(result)
        else:
            # Fallback to individual processing
            return [self.embed(text) for text in texts]
    
    def _extract_single_embedding(self, result: Dict[str, Any]) -> np.ndarray:
        """Extract embedding from single prediction result."""
        if 'predictions' in result and result['predictions']:
            prediction = result['predictions'][0]
            
            # Try different embedding formats
            if 'cls_embedding' in prediction:
                return np.array(prediction['cls_embedding'])
            elif 'mean_embedding' in prediction:
                return np.array(prediction['mean_embedding'])
            elif 'embedding' in prediction:
                return np.array(prediction['embedding'])
            elif 'data' in prediction and isinstance(prediction['data'], list):
                # OpenAI format
                return np.array(prediction['data'])
        
        raise RuntimeError(f"Could not extract embedding from result: {result}")
    
    def _extract_batch_embeddings(self, result: Dict[str, Any]) -> List[np.ndarray]:
        """Extract embeddings from batch prediction result."""
        if 'predictions' in result and result['predictions']:
            embeddings = []
            for prediction in result['predictions']:
                if 'cls_embedding' in prediction:
                    embeddings.append(np.array(prediction['cls_embedding']))
                elif 'mean_embedding' in prediction:
                    embeddings.append(np.array(prediction['mean_embedding']))
                elif 'embedding' in prediction:
                    embeddings.append(np.array(prediction['embedding']))
                else:
                    raise RuntimeError(f"Could not extract embedding from prediction: {prediction}")
            return embeddings
        
        raise RuntimeError(f"Could not extract embeddings from batch result: {result}") 