"""
Tests for HuggingFaceModelWrapper.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.utils.models.huggingface import HuggingFaceModelWrapper


class TestHuggingFaceModelWrapper:
    """Tests for HuggingFaceModelWrapper class."""
    
    def test_init_without_torch(self):
        """Test initialization without torch raises ImportError."""
        with patch('src.utils.models.huggingface.HAS_TORCH', False):
            with pytest.raises(ImportError, match="torch and transformers are required"):
                HuggingFaceModelWrapper("bert-base-uncased")
    
    def test_init_unsupported_task(self):
        """Test initialization with unsupported task raises ValueError."""
        with patch('src.utils.models.huggingface.HAS_TORCH', True):
            with pytest.raises(ValueError, match="Unsupported task: unsupported"):
                HuggingFaceModelWrapper("bert-base-uncased", task="unsupported")
    
    @patch('src.utils.models.huggingface.HAS_TORCH', True)
    @patch('src.utils.models.huggingface.AutoTokenizer')
    @patch('src.utils.models.huggingface.AutoModelForTokenClassification')
    @patch('src.utils.models.huggingface.torch')
    def test_init_token_classification(self, mock_torch, mock_model_class, mock_tokenizer):
        """Test initialization for token classification."""
        # Setup mocks
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model = Mock()
        mock_model.config.id2label = {0: 'O', 1: 'B-VARIANT'}
        mock_model.config.label2id = {'O': 0, 'B-VARIANT': 1}
        mock_model_class.from_pretrained.return_value = mock_model
        mock_torch.device.return_value = "cpu"
        mock_torch.cuda.is_available.return_value = False
        
        # Create wrapper
        wrapper = HuggingFaceModelWrapper("bert-base-uncased", task="token-classification")
        
        # Assertions
        assert wrapper.model_name == "bert-base-uncased"
        assert wrapper.task == "token-classification"
        assert wrapper.is_loaded == True
        mock_tokenizer.from_pretrained.assert_called_once_with("bert-base-uncased")
        mock_model_class.from_pretrained.assert_called_once_with("bert-base-uncased")
    
    @patch('src.utils.models.huggingface.HAS_TORCH', True)
    @patch('src.utils.models.huggingface.AutoTokenizer')
    @patch('src.utils.models.huggingface.AutoModel')
    @patch('src.utils.models.huggingface.torch')
    def test_init_embeddings(self, mock_torch, mock_model_class, mock_tokenizer):
        """Test initialization for embeddings."""
        # Setup mocks
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model = Mock()
        mock_model_class.from_pretrained.return_value = mock_model
        mock_torch.device.return_value = "cpu"
        mock_torch.cuda.is_available.return_value = False
        
        # Create wrapper
        wrapper = HuggingFaceModelWrapper("sentence-transformers/all-MiniLM-L6-v2", task="embeddings")
        
        # Assertions
        assert wrapper.task == "embeddings"
        assert wrapper.is_loaded == True
        mock_model_class.from_pretrained.assert_called_once()
    
    @patch('src.utils.models.huggingface.HAS_TORCH', True)
    @patch('src.utils.models.huggingface.torch')
    def test_get_device_cpu(self, mock_torch):
        """Test device selection - CPU."""
        mock_torch.device.return_value = "cpu"
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        
        with patch.object(HuggingFaceModelWrapper, 'load_model'):
            wrapper = HuggingFaceModelWrapper("bert-base-uncased")
            device = wrapper._get_device()
            
        mock_torch.device.assert_called_with("cpu")
        assert device == "cpu"
    
    @patch('src.utils.models.huggingface.HAS_TORCH', True)
    @patch('src.utils.models.huggingface.torch')
    def test_get_device_cuda(self, mock_torch):
        """Test device selection - CUDA."""
        mock_torch.device.return_value = "cuda"
        mock_torch.cuda.is_available.return_value = True
        
        with patch.object(HuggingFaceModelWrapper, 'load_model'):
            wrapper = HuggingFaceModelWrapper("bert-base-uncased")
            device = wrapper._get_device()
            
        mock_torch.device.assert_called_with("cuda")
        assert device == "cuda"
    
    @patch('src.utils.models.huggingface.HAS_TORCH', True)
    @patch('src.utils.models.huggingface.torch')
    def test_get_device_force_cpu(self, mock_torch):
        """Test device selection - forced CPU."""
        mock_torch.device.return_value = "cpu"
        mock_torch.cuda.is_available.return_value = True  # CUDA available but forced CPU
        
        with patch.object(HuggingFaceModelWrapper, 'load_model'):
            wrapper = HuggingFaceModelWrapper("bert-base-uncased")
            device = wrapper._get_device(force_cpu=True)
            
        mock_torch.device.assert_called_with("cpu")
        assert device == "cpu"
    
    def test_unload_model(self):
        """Test model unloading."""
        with patch.object(HuggingFaceModelWrapper, 'load_model'):
            wrapper = HuggingFaceModelWrapper("bert-base-uncased")
            wrapper.is_loaded = True
            wrapper.model = Mock()
            wrapper.tokenizer = Mock()
            
            with patch('src.utils.models.huggingface.gc') as mock_gc, \
                 patch('src.utils.models.huggingface.torch') as mock_torch:
                mock_torch.cuda.is_available.return_value = True
                
                wrapper.unload_model()
                
                assert wrapper.is_loaded == False
                assert wrapper.model is None
                assert wrapper.tokenizer is None
                mock_gc.collect.assert_called_once()
                mock_torch.cuda.empty_cache.assert_called_once()
    
    def test_tokenize_text_not_loaded(self):
        """Test tokenization when model is not loaded."""
        with patch.object(HuggingFaceModelWrapper, 'load_model'):
            wrapper = HuggingFaceModelWrapper("bert-base-uncased")
            wrapper.is_loaded = False
            wrapper.tokenizer = None
            
            with pytest.raises(RuntimeError, match="Tokenizer is not loaded"):
                wrapper.tokenize_text("test text")
    
    def test_predict_not_loaded(self):
        """Test prediction when model is not loaded."""
        with patch.object(HuggingFaceModelWrapper, 'load_model'):
            wrapper = HuggingFaceModelWrapper("bert-base-uncased")
            wrapper.is_loaded = False
            
            with pytest.raises(RuntimeError, match="Model is not loaded"):
                wrapper.predict("test text")
    
    def test_reconstruct_text(self):
        """Test text reconstruction from tokens."""
        with patch.object(HuggingFaceModelWrapper, 'load_model'):
            wrapper = HuggingFaceModelWrapper("bert-base-uncased")
            
            # Test with BERT-style subword tokens
            tokens = ["hello", "##world", "test"]
            result = wrapper._reconstruct_text(tokens)
            assert result == "helloworld test"  # "hello" + "world" + " test" 
            
            # Test with SentencePiece-style tokens
            tokens = ["▁hello", "▁world", "test"]
            result = wrapper._reconstruct_text(tokens)
            assert result == "hello world test"
    
    @patch('src.utils.models.huggingface.HAS_TORCH', True)
    def test_predict_token_classification(self):
        """Test prediction for token classification."""
        with patch.object(HuggingFaceModelWrapper, 'load_model'):
            wrapper = HuggingFaceModelWrapper("bert-base-uncased", task="token-classification")
            wrapper.is_loaded = True
            wrapper.tokenizer = Mock()
            wrapper.model = Mock()
            wrapper.id2label = {0: 'O', 1: 'B-VARIANT', 2: 'I-VARIANT'}
            
            # Mock tokenization
            mock_encoding = Mock()
            mock_encoding.input_ids = [[101, 1234, 102]]  # Mock input IDs
            wrapper.tokenize_text = Mock(return_value=mock_encoding)
            
            # Mock model outputs
            mock_outputs = Mock()
            mock_logits = Mock()
            mock_outputs.logits = mock_logits
            wrapper.model.return_value = mock_outputs
            
            # Mock torch operations
            with patch('src.utils.models.huggingface.torch') as mock_torch:
                # Create a proper mock for predictions that supports indexing
                mock_predictions = [0, 1, 0]  # Simple list instead of Mock
                mock_torch.argmax.return_value = mock_predictions
                mock_torch.no_grad.return_value.__enter__ = Mock(return_value=None)
                mock_torch.no_grad.return_value.__exit__ = Mock(return_value=None)
                
                # Mock tensor item() method
                mock_item_objects = [Mock(), Mock(), Mock()]
                mock_item_objects[0].item.return_value = 0
                mock_item_objects[1].item.return_value = 1  
                mock_item_objects[2].item.return_value = 0
                
                # Make the predictions indexable
                def mock_getitem(index):
                    return mock_item_objects[index]
                
                mock_predictions_tensor = Mock()
                mock_predictions_tensor.__getitem__ = mock_getitem
                mock_torch.argmax.return_value = mock_predictions_tensor
                
                # Mock tokenizer operations
                wrapper.tokenizer.convert_ids_to_tokens.return_value = ["[CLS]", "variant", "[SEP]"]
                
                result = wrapper.predict("test variant text")
                
                assert 'predictions' in result
                assert result['model_name'] == "bert-base-uncased"
                assert result['task'] == "token-classification"
    
    def test_get_supported_labels(self):
        """Test getting supported labels."""
        with patch.object(HuggingFaceModelWrapper, 'load_model'):
            wrapper = HuggingFaceModelWrapper("bert-base-uncased")
            wrapper.id2label = {0: 'O', 1: 'B-VARIANT'}
            
            labels = wrapper.get_supported_labels()
            assert labels == {0: 'O', 1: 'B-VARIANT'}
    
    def test_batch_predict(self):
        """Test batch prediction."""
        with patch.object(HuggingFaceModelWrapper, 'load_model'):
            wrapper = HuggingFaceModelWrapper("bert-base-uncased")
            
            # Mock the predict method
            wrapper.predict = Mock()
            wrapper.predict.side_effect = [
                {'predictions': [{'text': 'text1', 'entities': []}]},
                {'predictions': [{'text': 'text2', 'entities': []}]},
                {'predictions': [{'text': 'text3', 'entities': []}]}
            ]
            
            texts = ["text1", "text2", "text3"]
            result = wrapper.batch_predict(texts, batch_size=2)
            
            assert 'predictions' in result
            assert result['total_processed'] == 3
            assert len(result['predictions']) == 3
    
    def test_context_manager(self):
        """Test context manager functionality."""
        with patch.object(HuggingFaceModelWrapper, 'load_model') as mock_load, \
             patch.object(HuggingFaceModelWrapper, 'unload_model') as mock_unload:
            
            wrapper = HuggingFaceModelWrapper("bert-base-uncased")
            wrapper.is_loaded = False
            
            with wrapper:
                mock_load.assert_called()
                # Set is_loaded to True after load_model is called to simulate normal behavior
                wrapper.is_loaded = True
            
            mock_unload.assert_called() 