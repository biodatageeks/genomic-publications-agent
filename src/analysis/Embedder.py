from src.utils.models.generic import GenericEmbedder
from src.utils.config.config import Config


class Embedder:
    """
    Text embedder using the generic embedder system.
    
    This class provides backward compatibility while using the new
    unified embedding system that supports multiple model types.
    """

    def __init__(self, model_name=None, provider=None, **kwargs):
        """
        Initialize the embedder.
        
        Args:
            model_name: Name of the embedding model. If None, uses default from config
            provider: Provider for the model (e.g., 'openai', 'huggingface') 
            **kwargs: Additional arguments for model initialization
        """
        self.config = Config()
        
        if model_name is None:
            # Get default from configuration
            model_name = self.config.get_default_embedding_model()
            
        self.model_name = model_name
        self.provider = provider
        
        # Use the new generic embedder system
        self.generic_embedder = GenericEmbedder(
            model_name=model_name, 
            provider=provider, 
            max_length=kwargs.get('max_length', 512),
            **kwargs
        )
        
        # For backward compatibility
        self.model_wrapper = self.generic_embedder.model_wrapper

    def embed(self, chunk):
        """
        Generate embeddings for the given text chunk.
        
        Args:
            chunk: Text to embed
            
        Returns:
            Numpy array with embeddings
        """
        return self.generic_embedder.embed(chunk)
    
    def embed_batch(self, chunks, batch_size=8):
        """
        Generate embeddings for multiple text chunks efficiently.
        
        Args:
            chunks: List of texts to embed
            batch_size: Size of processing batches
            
        Returns:
            List of embedding arrays
        """
        return self.generic_embedder.embed_batch(chunks, batch_size=batch_size)
