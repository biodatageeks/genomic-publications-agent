"""
Generic chat interface for unified conversational AI across different model types.
"""

import logging
from typing import Dict, Any, Optional

from ..factory import ModelFactory
from ..base import BaseModelWrapper
from ...config.config import Config


class GenericChat:
    """
    Universal chat interface that works with any conversational model.
    
    Supports:
    - OpenAI models
    - Together AI models
    - HuggingFace conversational models
    - Custom chat models
    """
    
    def __init__(self, model_name: Optional[str] = None, provider: Optional[str] = None, **kwargs):
        """
        Initialize the chat model.
        
        Args:
            model_name: Name of the chat model. If None, uses default from config
            provider: Provider for the model (e.g., 'openai', 'together'). If None, uses default from config
            **kwargs: Additional arguments for model initialization
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = Config()
        
        if model_name is None:
            # Get default from configuration
            model_name = self.config.get_default_chat_model()
            
        if provider is None:
            # Get default provider from configuration
            provider = self.config.get_default_chat_provider()
            
        self.model_name = model_name
        self.provider = provider
        
        # Create LLM wrapper
        if provider:
            self.model_wrapper = ModelFactory.create_llm(model_name, provider=provider, **kwargs)
        else:
            self.model_wrapper = ModelFactory.create(model_name, provider=provider, **kwargs)
            
        self.logger.info(f"Initialized chat with {self.model_wrapper.get_model_type()} model: {model_name}")
    
    def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a message to the chat model.
        
        Args:
            message: User message
            system_prompt: Optional system prompt
            
        Returns:
            Model response
        """
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {message}\n\nAssistant:"
        else:
            full_prompt = message
            
        result = self.model_wrapper.predict(full_prompt)
        return self._extract_response(result)
    
    def generate(self, prompt: str) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated text
        """
        result = self.model_wrapper.predict(prompt)
        return self._extract_response(result)
    
    def _extract_response(self, result: Dict[str, Any]) -> str:
        """Extract text response from prediction result."""
        if 'predictions' in result and result['predictions']:
            prediction = result['predictions'][0]
            if isinstance(prediction, dict):
                if 'generated_text' in prediction:
                    return prediction['generated_text']
                elif 'text' in prediction:
                    return prediction['text']
                elif 'response' in prediction:
                    return prediction['response']
            elif isinstance(prediction, str):
                return prediction
        
        # Fallback: try to extract from top-level result
        if isinstance(result, str):
            return result
        elif 'text' in result:
            return result['text']
        elif 'response' in result:
            return result['response']
            
        raise RuntimeError(f"Could not extract response from result: {result}") 