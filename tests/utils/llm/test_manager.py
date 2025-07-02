"""
Tests for LLM manager.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from src.utils.llm import LlmManager

@pytest.fixture
def mock_config():
    """Mock Config class."""
    with patch('src.core.llm.manager.Config') as mock:
        config = MagicMock()
        config.get_llm_model_name.return_value = 'test-model'
        config.get_openai_api_key.return_value = 'test-openai-key'
        config.get_together_api_key.return_value = 'test-together-key'
        mock.return_value = config
        yield config

@pytest.fixture
def mock_getpass():
    """Mock getpass function."""
    with patch('src.core.llm.manager.getpass') as mock:
        mock.return_value = 'test-key'
        yield mock

def test_init_with_gpt(mock_config, mock_getpass):
    """Test initialization with GPT endpoint."""
    manager = LlmManager(endpoint='gpt')
    assert manager.llm_model_name == 'test-model'
    assert os.environ.get('OPENAI_API_KEY') == 'test-openai-key'

def test_init_with_together(mock_config, mock_getpass):
    """Test initialization with Together endpoint."""
    manager = LlmManager(endpoint='together')
    assert manager.llm_model_name == 'test-model'
    assert os.environ.get('TOGETHER_API_KEY') == 'test-together-key'

def test_init_with_invalid_endpoint(mock_config):
    """Test initialization with invalid endpoint."""
    with pytest.raises(ValueError, match='Invalid LLM endpoint: invalid'):
        LlmManager(endpoint='invalid')

def test_get_llm(mock_config):
    """Test getting LLM instance."""
    manager = LlmManager(endpoint='gpt')
    assert manager.get_llm() is not None

def test_get_llm_model_name(mock_config):
    """Test getting LLM model name."""
    manager = LlmManager(endpoint='gpt')
    assert manager.get_llm_model_name() == 'test-model'

def test_init_with_custom_model_name(mock_config):
    """Test initialization with custom model name."""
    manager = LlmManager(endpoint='gpt', llm_model_name='custom-model')
    assert manager.llm_model_name == 'custom-model'

def test_init_with_custom_temperature(mock_config):
    """Test initialization with custom temperature."""
    manager = LlmManager(endpoint='gpt', temperature=0.5)
    assert manager.llm.temperature == 0.5 