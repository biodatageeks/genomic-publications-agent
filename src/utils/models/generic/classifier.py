"""
Generic classifier for unified text classification across different model types.
"""

import logging
from typing import List, Dict, Any, Optional, Union

from ..factory import ModelFactory
from ..base import BaseModelWrapper
from ...config.config import Config


class GenericClassifier:
    """
    Universal text classifier that works with any classification model.
    
    Supports:
    - HuggingFace classification models
    - Custom classification models
    - Multi-class and multi-label classification
    """
    
    def __init__(self, model_name: Optional[str] = None, provider: Optional[str] = None, **kwargs):
        """
        Initialize the classifier.
        
        Args:
            model_name: Name of the classification model. If None, uses default from config
            provider: Provider for the model
            **kwargs: Additional arguments for model initialization
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = Config()
        
        if model_name is None:
            # Get default from configuration
            model_name = self.config.get_default_classification_model()
            
        self.model_name = model_name
        self.provider = provider
        
        # Create model wrapper for classification
        self.model_wrapper = ModelFactory.create(model_name, task="sequence-classification", provider=provider, **kwargs)
        
        self.logger.info(f"Initialized classifier with {self.model_wrapper.get_model_type()} model: {model_name}")
    
    def classify(self, text: Union[str, List[str]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Classify text(s).
        
        Args:
            text: Single text or list of texts to classify
            
        Returns:
            Classification result(s) with labels and confidence scores
        """
        result = self.model_wrapper.predict(text)
        
        if isinstance(text, str):
            return self._extract_single_classification(result)
        else:
            return self._extract_batch_classifications(result)
    
    def get_labels(self) -> Optional[Dict[int, str]]:
        """
        Get available classification labels.
        
        Returns:
            Dictionary mapping class IDs to labels
        """
        return self.model_wrapper.get_id2label()
    
    def _extract_single_classification(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract classification from single prediction result."""
        if 'predictions' in result and result['predictions']:
            prediction = result['predictions'][0]
            
            if 'predicted_label' in prediction:
                return {
                    'label': prediction['predicted_label'],
                    'confidence': prediction.get('confidence', 1.0),
                    'all_scores': prediction.get('all_scores', [])
                }
        
        raise RuntimeError(f"Could not extract classification from result: {result}")
    
    def _extract_batch_classifications(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract classifications from batch prediction result."""
        if 'predictions' in result and result['predictions']:
            classifications = []
            for prediction in result['predictions']:
                if 'predicted_label' in prediction:
                    classifications.append({
                        'label': prediction['predicted_label'],
                        'confidence': prediction.get('confidence', 1.0),
                        'all_scores': prediction.get('all_scores', [])
                    })
                else:
                    raise RuntimeError(f"Could not extract classification from prediction: {prediction}")
            return classifications
        
        raise RuntimeError(f"Could not extract classifications from batch result: {result}") 