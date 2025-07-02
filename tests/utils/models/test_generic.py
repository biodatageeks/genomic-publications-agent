"""
Tests for generic utility classes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from src.utils.models.generic import GenericEmbedder, GenericTokenizer, GenericChat, GenericClassifier


class TestGenericEmbedder:
    """Test GenericEmbedder class."""
    
    def test_init_with_default_model(self):
        """Test initialization with default model."""
        with patch('src.utils.models.factory.ModelFactory.create') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "huggingface"
            mock_create.return_value = mock_wrapper
            
            embedder = GenericEmbedder()
            
            assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"
            assert embedder.provider is None
            mock_create.assert_called_once()
    
    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        with patch('src.utils.models.factory.ModelFactory.create') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "huggingface"
            mock_create.return_value = mock_wrapper
            
            embedder = GenericEmbedder("custom-model", provider="openai")
            
            assert embedder.model_name == "custom-model"
            assert embedder.provider == "openai"
    
    def test_embed_single_text(self):
        """Test embedding single text."""
        with patch('src.utils.models.factory.ModelFactory.create') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "huggingface"
            mock_wrapper.predict.return_value = {
                'predictions': [{'cls_embedding': [0.1, 0.2, 0.3]}]
            }
            mock_create.return_value = mock_wrapper
            
            embedder = GenericEmbedder()
            result = embedder.embed("test text")
            
            assert isinstance(result, np.ndarray)
            assert result.tolist() == [0.1, 0.2, 0.3]
    
    def test_embed_batch_text(self):
        """Test embedding batch of texts."""
        with patch('src.utils.models.factory.ModelFactory.create') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "huggingface"
            mock_wrapper.predict.return_value = {
                'predictions': [
                    {'cls_embedding': [0.1, 0.2, 0.3]},
                    {'cls_embedding': [0.4, 0.5, 0.6]}
                ]
            }
            mock_create.return_value = mock_wrapper
            
            embedder = GenericEmbedder()
            result = embedder.embed(["test text 1", "test text 2"])
            
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0].tolist() == [0.1, 0.2, 0.3]
            assert result[1].tolist() == [0.4, 0.5, 0.6]


class TestGenericTokenizer:
    """Test GenericTokenizer class."""
    
    def test_init_with_default_model(self):
        """Test initialization with default model."""
        with patch('src.utils.models.factory.ModelFactory.create') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "huggingface"
            mock_create.return_value = mock_wrapper
            
            tokenizer = GenericTokenizer()
            
            assert tokenizer.model_name == "bert-base-uncased"
            assert tokenizer.provider is None
    
    def test_tokenize_text(self):
        """Test text tokenization."""
        with patch('src.utils.models.factory.ModelFactory.create') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "huggingface"
            mock_wrapper.tokenize_text.return_value = {"tokens": ["hello", "world"]}
            mock_create.return_value = mock_wrapper
            
            tokenizer = GenericTokenizer()
            result = tokenizer.tokenize("hello world")
            
            assert result == {"tokens": ["hello", "world"]}
            mock_wrapper.tokenize_text.assert_called_once_with("hello world")


class TestGenericChat:
    """Test GenericChat class."""
    
    def test_init_with_default_model(self):
        """Test initialization with default model."""
        with patch('src.utils.models.factory.ModelFactory.create_llm') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "llm"
            mock_create.return_value = mock_wrapper
            
            chat = GenericChat()
            
            assert chat.model_name == "meta-llama/Meta-Llama-3.1-8B-Instruct"
            assert chat.provider == "together"
    
    def test_chat_with_system_prompt(self):
        """Test chat with system prompt."""
        with patch('src.utils.models.factory.ModelFactory.create_llm') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "llm"
            mock_wrapper.predict.return_value = {
                'predictions': [{'generated_text': 'Hello! How can I help you?'}]
            }
            mock_create.return_value = mock_wrapper
            
            chat = GenericChat()
            result = chat.chat("Hi there", system_prompt="You are a helpful assistant")
            
            assert result == "Hello! How can I help you?"
    
    def test_generate_text(self):
        """Test text generation."""
        with patch('src.utils.models.factory.ModelFactory.create_llm') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "llm"
            mock_wrapper.predict.return_value = {
                'predictions': [{'generated_text': 'Generated response'}]
            }
            mock_create.return_value = mock_wrapper
            
            chat = GenericChat()
            result = chat.generate("Generate some text")
            
            assert result == "Generated response"


class TestGenericClassifier:
    """Test GenericClassifier class."""
    
    def test_init_with_default_model(self):
        """Test initialization with default model."""
        with patch('src.utils.models.factory.ModelFactory.create') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "huggingface"
            mock_create.return_value = mock_wrapper
            
            classifier = GenericClassifier()
            
            assert classifier.model_name == "cardiffnlp/twitter-roberta-base-sentiment-latest"
            assert classifier.provider is None
    
    def test_classify_single_text(self):
        """Test classification of single text."""
        with patch('src.utils.models.factory.ModelFactory.create') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "huggingface"
            mock_wrapper.predict.return_value = {
                'predictions': [{
                    'predicted_label': 'POSITIVE',
                    'confidence': 0.95,
                    'all_scores': [{'label': 'POSITIVE', 'score': 0.95}]
                }]
            }
            mock_create.return_value = mock_wrapper
            
            classifier = GenericClassifier()
            result = classifier.classify("This is great!")
            
            assert result['label'] == 'POSITIVE'
            assert result['confidence'] == 0.95
    
    def test_get_labels(self):
        """Test getting classification labels."""
        with patch('src.utils.models.factory.ModelFactory.create') as mock_create:
            mock_wrapper = Mock()
            mock_wrapper.get_model_type.return_value = "huggingface"
            mock_wrapper.get_id2label.return_value = {0: 'NEGATIVE', 1: 'POSITIVE'}
            mock_create.return_value = mock_wrapper
            
            classifier = GenericClassifier()
            labels = classifier.get_labels()
            
            assert labels == {0: 'NEGATIVE', 1: 'POSITIVE'} 