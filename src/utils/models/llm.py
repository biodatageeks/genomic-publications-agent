"""
LLM model wrapper implementation.

This module provides a wrapper for Language Models (LLM) that uses
the LlmApiProvider for API interactions.
"""

from typing import Any, Dict, List, Optional, Union

from .base import BaseModelWrapper
from src.utils.llm.provider import LlmApiProvider


class LLMModelWrapper(BaseModelWrapper):
    """
    Wrapper for Language Models (LLM) that uses LlmApiProvider.
    
    This wrapper provides a unified interface for LLM models while
    using the LlmApiProvider for API interactions.
    
    Features:
    - Unified interface with other model wrappers
    - Built on top of LlmApiProvider
    - Support for multiple LLM providers (OpenAI, Together, etc.)
    - Prompt engineering and response processing
    """
    
    def __init__(self, model_name: str, provider: Optional[str] = None, 
                 temperature: float = 0.0, **kwargs):
        """
        Initialize LLM model wrapper.
        
        Args:
            model_name: Name of the LLM model
            provider: LLM provider ('openai', 'together', etc.)
            temperature: Sampling temperature for generation
            **kwargs: Additional configuration parameters
        """
        super().__init__(model_name, **kwargs)
        
        self.provider = provider
        self.temperature = temperature
        self.llm_provider = None
        self.llm = None
        
        # Auto-load model during initialization
        self.load_model()
    
    def load_model(self) -> None:
        """Load the LLM model using LlmApiProvider."""
        if self.is_loaded:
            self.logger.warning(f"LLM model {self.model_name} is already loaded")
            return
        
        try:
            self.logger.info(f"Loading LLM model: {self.model_name}")
            
            # Initialize LlmApiProvider
            self.llm_provider = LlmApiProvider(
                provider=self.provider,
                model_name=self.model_name,
                temperature=self.temperature
            )
            
            # Get the LLM instance
            self.llm = self.llm_provider.get_llm()
            
            self.is_loaded = True
            self.logger.info(f"LLM model {self.model_name} loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load LLM model {self.model_name}: {e}")
            self.unload_model()
            raise
    
    def unload_model(self) -> None:
        """Unload the LLM model and free resources."""
        if not self.is_loaded:
            return
        
        try:
            self.logger.info(f"Unloading LLM model {self.model_name}")
            
            # Clear LLM instances
            if self.llm is not None:
                del self.llm
                self.llm = None
            
            if self.llm_provider is not None:
                del self.llm_provider
                self.llm_provider = None
            
            self.is_loaded = False
            self.logger.info("LLM model unloaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error during LLM model unloading: {e}")
    
    def predict(self, input_data: Union[str, List[str], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate text using the LLM model.
        
        Args:
            input_data: Input for text generation. Can be:
                       - str: Simple prompt
                       - List[str]: Multiple prompts
                       - Dict: Complex prompt with parameters
                       
        Returns:
            Dictionary containing generated text and metadata
        """
        if not self.is_loaded:
            raise RuntimeError("LLM model is not loaded. Call load_model() first.")
        
        # Handle different input types
        if isinstance(input_data, str):
            prompts = [input_data]
        elif isinstance(input_data, list):
            prompts = input_data
        elif isinstance(input_data, dict):
            # Handle structured prompt
            prompts = [input_data.get('prompt', '')]
        else:
            raise ValueError(f"Unsupported input type: {type(input_data)}")
        
        results = []
        
        for prompt in prompts:
            try:
                # Generate response using LLM
                response = self.llm.invoke(prompt)
                
                # Process response
                if hasattr(response, 'content'):
                    # langchain response object
                    generated_text = response.content
                elif isinstance(response, str):
                    # simple string response
                    generated_text = response
                else:
                    # try to convert to string
                    generated_text = str(response)
                
                result = {
                    'prompt': prompt,
                    'generated_text': generated_text,
                    'model_name': self.model_name,
                    'provider': self.provider,
                    'temperature': self.temperature
                }
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error generating text for prompt '{prompt[:50]}...': {e}")
                results.append({
                    'prompt': prompt,
                    'error': str(e),
                    'model_name': self.model_name
                })
        
        return {
            'predictions': results,
            'model_name': self.model_name,
            'provider': self.provider,
            'temperature': self.temperature,
            'total_processed': len(prompts)
        }
    
    def generate_with_prompt_template(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Generate text using a prompt template with variables.
        
        Args:
            template: Prompt template with placeholders (e.g., "Analyze {text}")
            variables: Dictionary of variables to fill in template
            
        Returns:
            Generated text
        """
        if not self.is_loaded:
            raise RuntimeError("LLM model is not loaded. Call load_model() first.")
        
        # Fill template with variables
        try:
            filled_prompt = template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing variable in template: {e}")
        
        # Generate response
        result = self.predict(filled_prompt)
        
        if result['predictions'] and 'generated_text' in result['predictions'][0]:
            return result['predictions'][0]['generated_text']
        else:
            raise RuntimeError("Failed to generate text")
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Conduct a chat conversation with the LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            Generated response text
        """
        if not self.is_loaded:
            raise RuntimeError("LLM model is not loaded. Call load_model() first.")
        
        # Convert messages to a single prompt
        # This is a simple implementation - could be enhanced for better chat handling
        conversation = ""
        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'system':
                conversation += f"System: {content}\n\n"
            elif role == 'user':
                conversation += f"User: {content}\n\n"
            elif role == 'assistant':
                conversation += f"Assistant: {content}\n\n"
        
        conversation += "Assistant: "
        
        # Generate response
        result = self.predict(conversation)
        
        if result['predictions'] and 'generated_text' in result['predictions'][0]:
            return result['predictions'][0]['generated_text']
        else:
            raise RuntimeError("Failed to generate chat response")
    
    def batch_generate(self, prompts: List[str], batch_size: int = 4) -> Dict[str, Any]:
        """
        Generate text for multiple prompts in batches.
        
        Args:
            prompts: List of prompts to process
            batch_size: Number of prompts to process in each batch
            
        Returns:
            Dictionary containing all generated texts
        """
        all_results = []
        
        for i in range(0, len(prompts), batch_size):
            batch_prompts = prompts[i:i + batch_size]
            batch_result = self.predict(batch_prompts)
            all_results.extend(batch_result['predictions'])
        
        return {
            'predictions': all_results,
            'model_name': self.model_name,
            'provider': self.provider,
            'total_processed': len(prompts)
        }
    
    def get_llm_provider(self) -> Optional[LlmApiProvider]:
        """
        Get the underlying LlmApiProvider instance.
        
        Returns:
            LlmApiProvider instance or None if not loaded
        """
        return self.llm_provider
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the LLM provider and configuration.
        
        Returns:
            Dictionary with provider information
        """
        if self.llm_provider:
            return {
                'provider': self.llm_provider.get_provider(),
                'model_name': self.llm_provider.get_model_name(),
                'temperature': self.temperature,
                'supported_providers': LlmApiProvider.SUPPORTED_PROVIDERS,
                'default_models': LlmApiProvider.DEFAULT_MODELS
            }
        else:
            return {
                'provider': self.provider,
                'model_name': self.model_name,
                'temperature': self.temperature,
                'is_loaded': False
            } 