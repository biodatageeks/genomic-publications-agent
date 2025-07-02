"""
Tests for ModelFactory.
"""

import pytest
from unittest.mock import Mock, patch

from src.utils.models.factory import ModelFactory


class TestModelFactory:
    """Tests for ModelFactory class."""
    
    def test_detect_llm_models(self):
        """Test detection of LLM models."""
        llm_models = [
            "gpt-4",
            "gpt-3.5-turbo",
            "claude-3",
            "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-v0.1"
        ]
        
        for model_name in llm_models:
            model_type = ModelFactory._detect_model_type(model_name)
            assert model_type == 'llm', f"Failed to detect {model_name} as LLM"
    
    def test_detect_huggingface_models(self):
        """Test detection of HuggingFace models."""
        hf_models = [
            "bert-base-uncased",
            "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext",
            "distilbert-base-uncased",
            "roberta-large",
            "dmis-lab/biobert-v1.1",
            "allenai/scibert_scivocab_uncased",
            "microsoft/biobert",
            "some-org/ner-model"
        ]
        
        for model_name in hf_models:
            model_type = ModelFactory._detect_model_type(model_name)
            assert model_type == 'huggingface', f"Failed to detect {model_name} as HuggingFace"
    
    def test_detect_model_type_with_provider(self):
        """Test model type detection with provider hint."""
        model_type = ModelFactory._detect_model_type("some-model", provider="together")
        assert model_type == 'llm'
        
        model_type = ModelFactory._detect_model_type("unknown-model", provider="openai")
        assert model_type == 'llm'
    
    @patch('src.utils.models.factory.HuggingFaceModelWrapper')
    def test_create_huggingface_model(self, mock_hf_wrapper):
        """Test creating HuggingFace model wrapper."""
        mock_instance = Mock()
        mock_hf_wrapper.return_value = mock_instance
        
        result = ModelFactory.create_huggingface("bert-base-uncased", task="token-classification")
        
        mock_hf_wrapper.assert_called_once_with("bert-base-uncased", task="token-classification")
        assert result == mock_instance
    
    @patch('src.utils.models.factory.LLMModelWrapper')
    def test_create_llm_model(self, mock_llm_wrapper):
        """Test creating LLM model wrapper."""
        mock_instance = Mock()
        mock_llm_wrapper.return_value = mock_instance
        
        result = ModelFactory.create_llm("gpt-4", provider="openai")
        
        mock_llm_wrapper.assert_called_once_with("gpt-4", provider="openai")
        assert result == mock_instance
    
    @patch('src.utils.models.factory.ModelFactory._create_huggingface_wrapper')
    @patch('src.utils.models.factory.ModelFactory._detect_model_type')
    def test_create_auto_huggingface(self, mock_detect, mock_create_hf):
        """Test auto-creation of HuggingFace wrapper."""
        mock_detect.return_value = 'huggingface'
        mock_instance = Mock()
        mock_create_hf.return_value = mock_instance
        
        result = ModelFactory.create("bert-base-uncased", model_type="auto")
        
        mock_detect.assert_called_once_with("bert-base-uncased", None)
        mock_create_hf.assert_called_once_with("bert-base-uncased")
        assert result == mock_instance
    
    @patch('src.utils.models.factory.ModelFactory._create_llm_wrapper')
    @patch('src.utils.models.factory.ModelFactory._detect_model_type')
    def test_create_auto_llm(self, mock_detect, mock_create_llm):
        """Test auto-creation of LLM wrapper."""
        mock_detect.return_value = 'llm'
        mock_instance = Mock()
        mock_create_llm.return_value = mock_instance
        
        result = ModelFactory.create("gpt-4", model_type="auto", provider="openai")
        
        mock_detect.assert_called_once_with("gpt-4", "openai")
        mock_create_llm.assert_called_once_with("gpt-4", "openai")
        assert result == mock_instance
    
    def test_create_unsupported_model_type(self):
        """Test error handling for unsupported model type."""
        with pytest.raises(ValueError, match="Unsupported model type: unsupported"):
            ModelFactory.create("some-model", model_type="unsupported")
    
    @patch('src.utils.models.factory.HuggingFaceModelWrapper')
    def test_create_token_classifier(self, mock_hf_wrapper):
        """Test creating token classification model."""
        mock_instance = Mock()
        mock_hf_wrapper.return_value = mock_instance
        
        result = ModelFactory.create_token_classifier("bert-base-uncased")
        
        mock_hf_wrapper.assert_called_once_with("bert-base-uncased", task="token-classification")
        assert result == mock_instance
    
    @patch('src.utils.models.factory.HuggingFaceModelWrapper')
    def test_create_embedder(self, mock_hf_wrapper):
        """Test creating embedding model."""
        mock_instance = Mock()
        mock_hf_wrapper.return_value = mock_instance
        
        result = ModelFactory.create_embedder("sentence-transformers/all-MiniLM-L6-v2")
        
        mock_hf_wrapper.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2", task="embeddings")
        assert result == mock_instance
    
    def test_get_supported_tasks(self):
        """Test getting supported tasks."""
        tasks = ModelFactory.get_supported_tasks()
        
        assert 'huggingface' in tasks
        assert 'llm' in tasks
        assert isinstance(tasks['huggingface'], list)
        assert isinstance(tasks['llm'], list)
    
    def test_is_model_supported(self):
        """Test checking if model is supported."""
        assert ModelFactory.is_model_supported("bert-base-uncased") == True
        assert ModelFactory.is_model_supported("gpt-4") == True
        assert ModelFactory.is_model_supported("unknown-model") == True  # defaults to HF
    
    def test_list_model_patterns(self):
        """Test getting model patterns."""
        patterns = ModelFactory.list_model_patterns()
        
        assert 'llm' in patterns
        assert 'huggingface' in patterns
        assert 'llm_providers' in patterns
        assert isinstance(patterns['llm'], list)
        assert isinstance(patterns['huggingface'], list)
        assert isinstance(patterns['llm_providers'], list)
    
    @patch('src.utils.models.factory.HuggingFaceModelWrapper')
    def test_create_huggingface_wrapper_error(self, mock_hf_wrapper):
        """Test error handling in HuggingFace wrapper creation."""
        mock_hf_wrapper.side_effect = Exception("Model loading failed")
        
        with pytest.raises(ValueError, match="Failed to create HuggingFace wrapper"):
            ModelFactory._create_huggingface_wrapper("invalid-model")
    
    @patch('src.utils.models.factory.LLMModelWrapper')
    def test_create_llm_wrapper_error(self, mock_llm_wrapper):
        """Test error handling in LLM wrapper creation."""
        mock_llm_wrapper.side_effect = Exception("LLM loading failed")
        
        with pytest.raises(ValueError, match="Failed to create LLM wrapper"):
            ModelFactory._create_llm_wrapper("invalid-model") 