"""
Language Model Manager for handling interactions with LLM APIs.

This module provides a consistent interface for working with different
Language Model providers like OpenAI and TogetherAI.
"""

import logging
from typing import Optional, Dict, Any, List, Union

from langchain_openai import ChatOpenAI
from langchain_together import Together
from langchain_core.language_models.base import BaseLanguageModel

from src.utils.config.config import Config
from src.models.data.clients.exceptions import LLMError


class LlmManager:
    """
    Manager for Language Model (LLM) interactions.
    
    This class provides a unified interface for working with different LLM
    providers like OpenAI and TogetherAI, handling authentication, model
    selection, and API interactions.
    
    Example usage:
        llm_manager = LlmManager('openai', 'gpt-4')
        llm = llm_manager.get_llm()
        response = llm.invoke([HumanMessage(content="What is genomics?")])
    """
    
    # Supported LLM providers
    SUPPORTED_PROVIDERS = ['openai', 'together']
    
    # Default models for each provider
    DEFAULT_MODELS = {
        'openai': 'gpt-4',
        'together': 'meta-llama/Meta-Llama-3.1-8B-Instruct'
    }
    
    # Model temperature settings
    DEFAULT_TEMPERATURE = 0.0
    
    def __init__(self, provider: str, model_name: Optional[str] = None, 
                 temperature: float = DEFAULT_TEMPERATURE):
        """
        Initializes the LLM Manager.
        
        Args:
            provider: LLM provider name ("openai" or "together")
            model_name: Name of the LLM model to use (provider-specific)
            temperature: Sampling temperature for generation (0.0-1.0)
            
        Raises:
            ValueError: If an unsupported provider is specified
        """
        self.logger = logging.getLogger(__name__)
        
        # Validate provider
        provider = provider.lower()
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported LLM provider: {provider}. "
                           f"Supported providers: {', '.join(self.SUPPORTED_PROVIDERS)}")
        
        self.provider = provider
        self.temperature = temperature
        
        # Load configuration
        self.config = Config()
        
        # Set model name based on provider
        if model_name is None:
            model_name = self.config.get_llm_model_name()
            if not model_name:
                model_name = self.DEFAULT_MODELS[provider]
                self.logger.info(f"Using default model for {provider}: {model_name}")
        
        self.model_name = model_name
        self.llm: Optional[BaseLanguageModel] = None
        
        # Initialize the LLM based on provider
        self._initialize_llm()
        
        self.logger.info(f"Initialized LLM Manager with provider: {provider}, model: {model_name}")
    
    def _initialize_llm(self) -> None:
        """
        Initializes the LLM client based on the selected provider.
        
        Raises:
            LLMError: If there's an issue initializing the LLM client
        """
        try:
            if self.provider == 'openai':
                api_key = self.config.get_openai_api_key()
                if api_key:
                    self.llm = ChatOpenAI(
                        model=self.model_name,
                        api_key=api_key,
                        temperature=self.temperature
                    )
                    self.logger.debug(f"Initialized OpenAI LLM with model: {self.model_name}")
                else:
                    raise LLMError("OpenAI API key not found")
                    
            elif self.provider == 'together':
                api_key = self.config.get_together_api_key()
                if api_key:
                    self.llm = Together(
                        model=self.model_name,
                        together_api_key=api_key,
                        temperature=self.temperature
                    )
                    self.logger.debug(f"Initialized TogetherAI LLM with model: {self.model_name}")
                else:
                    raise LLMError("Together API key not found")
            
        except Exception as e:
            error_msg = f"Failed to initialize LLM client for {self.provider}: {str(e)}"
            self.logger.error(error_msg)
            raise LLMError(error_msg) from e
    
    def get_llm(self) -> BaseLanguageModel:
        """
        Returns the LLM instance.
        
        Returns:
            Configured LLM instance
            
        Raises:
            LLMError: If the LLM is not properly initialized
        """
        if self.llm is None:
            raise LLMError("LLM is not initialized")
        
        return self.llm
    
    def get_model_name(self) -> str:
        """
        Returns the name of the currently configured model.
        
        Returns:
            Model name
        """
        return self.model_name
    
    def get_provider(self) -> str:
        """
        Returns the name of the LLM provider.
        
        Returns:
            Provider name
        """
        return self.provider 