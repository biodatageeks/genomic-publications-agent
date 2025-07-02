"""
Model factory for creating appropriate model wrapper instances.

This module provides a factory pattern implementation for creating
different types of model wrappers based on model names and configurations.
"""

import re
from typing import Any, Dict, Optional, Union

from .base import BaseModelWrapper
from .huggingface import HuggingFaceModelWrapper
from .llm import LLMModelWrapper


class ModelFactory:
    """
    Factory class for creating model wrapper instances.
    
    This factory automatically determines the appropriate wrapper type
    based on model names, providers, and configuration parameters.
    """
    
    # Patterns to detect model types
    LLM_PATTERNS = [
        r'^gpt-.*',           # OpenAI GPT models
        r'^claude-.*',        # Anthropic Claude models
        r'^meta-llama/.*',    # Meta Llama models
        r'^mistralai/.*',     # Mistral models
        r'^together/.*',      # Together models
        r'^openai/.*',        # OpenAI models with prefix
    ]
    
    HUGGINGFACE_PATTERNS = [
        r'^.*bert.*',         # BERT-like models
        r'^.*roberta.*',      # RoBERTa-like models
        r'^.*distilbert.*',   # DistilBERT models
        r'^.*electra.*',      # ELECTRA models
        r'^.*deberta.*',      # DeBERTa models
        r'^.*biobert.*',      # BioBERT models
        r'^.*clinicalbert.*', # ClinicalBERT models
        r'^.*pubmedbert.*',   # PubMedBERT models
        r'^.*scibert.*',      # SciBERT models
        r'^.*bluebert.*',     # BlueBERT models
        r'^.*ner.*',          # NER-specific models
        r'^.*token.*class.*', # Token classification models
        r'^.*sequence.*class.*', # Sequence classification models
        r'^.*embeddings.*',   # Embedding models
        r'^.*transformers.*', # General transformers
    ]
    
    # Known LLM providers
    LLM_PROVIDERS = ['openai', 'together', 'anthropic', 'huggingface_hub']
    
    @classmethod
    def create(cls, model_name: str, model_type: Optional[str] = None,
               provider: Optional[str] = None, **kwargs) -> BaseModelWrapper:
        """
        Create an appropriate model wrapper instance.
        
        Args:
            model_name: Name or path of the model
            model_type: Explicit model type ('huggingface', 'llm', 'auto')
            provider: Model provider for LLM models
            **kwargs: Additional configuration parameters
            
        Returns:
            Appropriate model wrapper instance
            
        Raises:
            ValueError: If model type cannot be determined or is unsupported
        """
        # Auto-detect model type if not specified
        if model_type is None or model_type == 'auto':
            model_type = cls._detect_model_type(model_name, provider)
        
        # Create appropriate wrapper
        if model_type == 'huggingface':
            return cls._create_huggingface_wrapper(model_name, **kwargs)
        elif model_type == 'llm':
            return cls._create_llm_wrapper(model_name, provider, **kwargs)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    @classmethod
    def create_huggingface(cls, model_name: str, task: str = 'token-classification',
                          **kwargs) -> HuggingFaceModelWrapper:
        """
        Create a HuggingFace model wrapper.
        
        Args:
            model_name: Name or path of the HuggingFace model
            task: Task type for the model
            **kwargs: Additional configuration parameters
            
        Returns:
            HuggingFaceModelWrapper instance
        """
        return cls._create_huggingface_wrapper(model_name, task=task, **kwargs)
    
    @classmethod
    def create_llm(cls, model_name: str, provider: Optional[str] = None,
                   **kwargs) -> LLMModelWrapper:
        """
        Create an LLM model wrapper.
        
        Args:
            model_name: Name of the LLM model
            provider: LLM provider
            **kwargs: Additional configuration parameters
            
        Returns:
            LLMModelWrapper instance
        """
        return cls._create_llm_wrapper(model_name, provider, **kwargs)
    
    @classmethod
    def create_token_classifier(cls, model_name: str, **kwargs) -> HuggingFaceModelWrapper:
        """
        Create a token classification model wrapper.
        
        Args:
            model_name: Name of the model
            **kwargs: Additional configuration parameters
            
        Returns:
            HuggingFaceModelWrapper configured for token classification
        """
        return cls._create_huggingface_wrapper(
            model_name, 
            task='token-classification', 
            **kwargs
        )
    
    @classmethod
    def create_embedder(cls, model_name: str, **kwargs) -> HuggingFaceModelWrapper:
        """
        Create an embedding model wrapper.
        
        Args:
            model_name: Name of the embedding model
            **kwargs: Additional configuration parameters
            
        Returns:
            HuggingFaceModelWrapper configured for embeddings
        """
        return cls._create_huggingface_wrapper(
            model_name, 
            task='embeddings', 
            **kwargs
        )
    
    @classmethod
    def _detect_model_type(cls, model_name: str, provider: Optional[str] = None) -> str:
        """
        Automatically detect model type based on name and provider.
        
        Args:
            model_name: Name of the model
            provider: Optional provider hint
            
        Returns:
            Detected model type ('huggingface' or 'llm')
        """
        model_name_lower = model_name.lower()
        
        # Check if provider indicates LLM
        if provider and provider.lower() in cls.LLM_PROVIDERS:
            return 'llm'
        
        # Check LLM patterns
        for pattern in cls.LLM_PATTERNS:
            if re.match(pattern, model_name_lower):
                return 'llm'
        
        # Check HuggingFace patterns
        for pattern in cls.HUGGINGFACE_PATTERNS:
            if re.search(pattern, model_name_lower):
                return 'huggingface'
        
        # Default heuristics
        if '/' in model_name and not model_name.startswith('meta-llama/'):
            # Looks like a HuggingFace model path (org/model)
            return 'huggingface'
        elif model_name.startswith(('gpt', 'claude', 'llama')):
            return 'llm'
        else:
            # Default to HuggingFace for unknown models
            return 'huggingface'
    
    @classmethod
    def _create_huggingface_wrapper(cls, model_name: str, **kwargs) -> HuggingFaceModelWrapper:
        """Create a HuggingFace model wrapper with error handling."""
        try:
            return HuggingFaceModelWrapper(model_name, **kwargs)
        except Exception as e:
            raise ValueError(f"Failed to create HuggingFace wrapper for {model_name}: {e}")
    
    @classmethod
    def _create_llm_wrapper(cls, model_name: str, provider: Optional[str] = None,
                           **kwargs) -> LLMModelWrapper:
        """Create an LLM model wrapper with error handling."""
        try:
            return LLMModelWrapper(model_name, provider=provider, **kwargs)
        except Exception as e:
            raise ValueError(f"Failed to create LLM wrapper for {model_name}: {e}")
    
    @classmethod
    def get_supported_tasks(cls) -> Dict[str, list]:
        """
        Get supported tasks for different model types.
        
        Returns:
            Dictionary of supported tasks by model type
        """
        return {
            'huggingface': HuggingFaceModelWrapper.SUPPORTED_TASKS,
            'llm': ['text-generation', 'chat', 'completion']
        }
    
    @classmethod
    def is_model_supported(cls, model_name: str, provider: Optional[str] = None) -> bool:
        """
        Check if a model is supported by the factory.
        
        Args:
            model_name: Name of the model to check
            provider: Optional provider
            
        Returns:
            True if model is supported, False otherwise
        """
        try:
            model_type = cls._detect_model_type(model_name, provider)
            return model_type in ['huggingface', 'llm']
        except Exception:
            return False
    
    @classmethod
    def list_model_patterns(cls) -> Dict[str, list]:
        """
        Get the patterns used for model type detection.
        
        Returns:
            Dictionary of patterns by model type
        """
        return {
            'llm': cls.LLM_PATTERNS,
            'huggingface': cls.HUGGINGFACE_PATTERNS,
            'llm_providers': cls.LLM_PROVIDERS
        } 