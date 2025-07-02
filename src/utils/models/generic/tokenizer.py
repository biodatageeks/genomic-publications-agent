"""
Generic tokenizer for unified text tokenization across different model types.
"""

import logging
from typing import List, Dict, Any, Optional

from ..factory import ModelFactory
from ...config.config import Config


class GenericTokenizer:
    """
    Universal tokenizer that works with any tokenization model.
    
    Supports:
    - HuggingFace tokenizers
    - OpenAI tokenizers
    - Custom tokenizers
    """
    
    def __init__(self, model_name: Optional[str] = None, provider: Optional[str] = None, **kwargs):
        """
        Initialize the tokenizer.
        
        Args:
            model_name: Name of the model/tokenizer. If None, uses default from config
            provider: Provider for the model
            **kwargs: Additional arguments for model initialization
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = Config()
        
        if model_name is None:
            # Get default from configuration
            model_name = self.config.get_default_tokenizer_model()
            
        self.model_name = model_name
        self.provider = provider
        
        # Create model wrapper for tokenization
        self.model_wrapper = ModelFactory.create(model_name, task="token-classification", provider=provider, **kwargs)
        
        if self.model_wrapper.get_model_type() != "huggingface":
            self.logger.warning("Tokenization is primarily supported for HuggingFace models")
            
        self.logger.info(f"Initialized tokenizer with {self.model_wrapper.get_model_type()} model: {model_name}")
    
    def tokenize(self, text: str) -> Dict[str, Any]:
        """
        Tokenize text.
        
        Args:
            text: Text to tokenize
            
        Returns:
            Dictionary with tokens and other tokenization info
        """
        if hasattr(self.model_wrapper, 'tokenize_text'):
            return self.model_wrapper.tokenize_text(text)
        else:
            raise RuntimeError(f"Tokenization not supported for {self.model_wrapper.get_model_type()} models")
    
    def encode(self, text: str) -> List[int]:
        """
        Encode text to token IDs.
        
        Args:
            text: Text to encode
            
        Returns:
            List of token IDs
        """
        result = self.tokenize(text)
        if hasattr(result, 'input_ids'):
            return result.input_ids[0].tolist()
        else:
            raise RuntimeError("Could not extract token IDs from tokenization result") 