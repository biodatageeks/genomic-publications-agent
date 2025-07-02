"""
Base model wrapper abstract class.

This module defines the abstract interface that all model wrappers must implement.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple
from pathlib import Path

from src.utils.config.config import Config


class BaseModelWrapper(ABC):
    """
    Abstract base class for all model wrappers.
    
    Provides a common interface and shared functionality for managing
    different types of models (HuggingFace, LLM, embeddings, etc.).
    
    Features:
    - Unified initialization and configuration
    - Device management (CPU/GPU)
    - Resource cleanup
    - Error handling and logging
    - Model loading and caching
    """
    
    def __init__(self, model_name: str, **kwargs):
        """
        Initialize the model wrapper.
        
        Args:
            model_name: Name/path of the model to load
            **kwargs: Additional configuration parameters
        """
        self.model_name = model_name
        self.config = Config()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = None
        self.device = None
        self.is_loaded = False
        
        # Store additional configuration
        self.kwargs = kwargs
        
        self.logger.info(f"Initializing {self.__class__.__name__} with model: {model_name}")
    
    @abstractmethod
    def load_model(self) -> None:
        """
        Load the model and associated components.
        
        This method should handle:
        - Model loading from disk/hub
        - Device placement
        - Any preprocessing setup
        """
        pass
    
    @abstractmethod
    def predict(self, input_data: Any) -> Any:
        """
        Make predictions using the loaded model.
        
        Args:
            input_data: Input data for prediction
            
        Returns:
            Model predictions
        """
        pass
    
    @abstractmethod
    def unload_model(self) -> None:
        """
        Unload the model and free resources.
        
        This method should clean up:
        - Model from memory
        - GPU memory if applicable
        - Temporary files
        """
        pass
    
    def is_model_loaded(self) -> bool:
        """
        Check if the model is currently loaded.
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self.is_loaded
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary containing model information
        """
        return {
            'model_name': self.model_name,
            'model_type': self.__class__.__name__,
            'is_loaded': self.is_loaded,
            'device': str(self.device) if self.device else None,
            'config': self.kwargs
        }
    
    def get_device(self) -> Optional[Any]:
        """
        Get the device used by the model.
        
        Returns:
            Device object or None if not set
        """
        return self.device
    
    def get_id2label(self) -> Optional[Dict[int, str]]:
        """
        Get the id2label mapping for classification models.
        
        Returns:
            Dictionary mapping class IDs to labels, or None if not applicable
        """
        return getattr(self, 'id2label', None)
    
    def get_model_type(self) -> str:
        """
        Get the type of the model wrapper.
        
        Returns:
            String indicating the model type (e.g., 'huggingface', 'llm', 'base')
        """
        class_name = self.__class__.__name__.lower()
        if 'huggingface' in class_name:
            return 'huggingface'
        elif 'llm' in class_name:
            return 'llm'
        else:
            return 'base'
    
    def _check_dependencies(self, dependencies: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if required dependencies are available.
        
        Args:
            dependencies: List of dependency names to check
            
        Returns:
            Tuple of (all_available, missing_dependencies)
        """
        missing = []
        
        for dep in dependencies:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)
        
        return len(missing) == 0, missing
    
    def _get_device(self, force_cpu: bool = False) -> Any:
        """
        Determine the appropriate device for model execution.
        
        Args:
            force_cpu: Force CPU usage even if GPU is available
            
        Returns:
            Device object (torch.device or equivalent)
        """
        # This will be overridden by specific implementations
        return "cpu"
    
    def __enter__(self):
        """Context manager entry."""
        if not self.is_loaded:
            self.load_model()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.is_loaded:
            self.unload_model()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            if self.is_loaded:
                self.unload_model()
        except Exception as e:
            # Log but don't raise in destructor
            if hasattr(self, 'logger'):
                self.logger.warning(f"Error during cleanup: {e}") 