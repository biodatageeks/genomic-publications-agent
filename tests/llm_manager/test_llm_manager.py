"""
Tests for the LlmManager class.

This module provides comprehensive tests for the LlmManager which is responsible
for creating and managing LLM instances from different providers (OpenAI, TogetherAI).

The tests are designed to run with both mocks and real API calls. To run with real API,
appropriate API keys must be set in the config file or environment variables.

To run only mocked tests:
pytest tests/llm_manager/test_llm_manager.py -m "not realapi"

To run all tests including real API calls:
pytest tests/llm_manager/test_llm_manager.py
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call
from typing import Dict, Any

import yaml
from langchain_together import ChatTogether
from langchain_openai import ChatOpenAI

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.LlmManager import LlmManager
from src.Config import Config


# Fixtures for testing
@pytest.fixture
def mock_config():
    """Creates a mock Config object"""
    mock = MagicMock(spec=Config)
    # Set up mock return values
    mock.get_together_api_key.return_value = "mock_together_api_key"
    mock.get_openai_api_key.return_value = "mock_openai_api_key"
    mock.get_llm_model_name.return_value = "mock_model_name"
    mock.get_contact_email.return_value = "mock_email@example.com"
    return mock


@pytest.fixture
def mock_getpass():
    """Creates a mock for getpass to avoid prompting during tests"""
    with patch('src.LlmManager.getpass') as mock:
        mock.return_value = "mock_user_input_api_key"
        yield mock


@pytest.fixture
def mock_logging():
    """Creates a mock for logger to avoid console output during tests"""
    with patch('src.LlmManager.logging.getLogger') as mock:
        mock_logger = MagicMock()
        mock.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def mock_chat_together():
    """Creates a mock for ChatTogether"""
    with patch('src.LlmManager.ChatTogether') as mock:
        mock_instance = MagicMock(spec=ChatTogether)
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_chat_openai():
    """Creates a mock for ChatOpenAI"""
    with patch('src.LlmManager.ChatOpenAI') as mock:
        mock_instance = MagicMock(spec=ChatOpenAI)
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def real_config():
    """Creates a real Config object for API testing"""
    return Config()


# Mark tests that make real API calls
realapi = pytest.mark.realapi

# Basic Initialization Tests
class TestLlmManagerInitialization:
    """Tests for LlmManager initialization"""

    def test_init_with_mocked_together_api(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test initialization with Together API using mocks"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            # Initialize with together endpoint
            manager = LlmManager('together', 'test-model')
            
            # Check that the right objects were called
            mock_config.get_together_api_key.assert_called_once()
            mock_chat_together.assert_called_once()
            
            # Check model name was set correctly
            assert manager.llm_model_name == 'test-model'
            # Check LLM object was created
            assert manager.llm is mock_chat_together.return_value

    def test_init_with_mocked_openai_api(self, mock_config, mock_getpass, mock_logging, mock_chat_openai):
        """Test initialization with OpenAI API using mocks"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            # Initialize with gpt endpoint
            manager = LlmManager('gpt', 'test-model')
            
            # Check that the right objects were called
            mock_config.get_openai_api_key.assert_called_once()
            mock_chat_openai.assert_called_once()
            
            # Check model name was set correctly
            assert manager.llm_model_name == 'test-model'
            # Check LLM object was created
            assert manager.llm is mock_chat_openai.return_value

    def test_init_with_default_model_name(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test initialization with default model name from config"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            # Initialize without model name
            manager = LlmManager('together')
            
            # Config should be checked for model name
            mock_config.get_llm_model_name.assert_called_once()
            
            # Check model name was set correctly from config
            assert manager.llm_model_name == mock_config.get_llm_model_name.return_value

    def test_init_with_invalid_endpoint(self, mock_config, mock_getpass, mock_logging):
        """Test initialization with invalid endpoint"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            # Initialize with invalid endpoint
            with pytest.raises(ValueError) as exc_info:
                LlmManager('invalid_endpoint')
            
            # Check error message
            assert "Invalid LLM endpoint" in str(exc_info.value)

    def test_get_llm(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test get_llm method"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            manager = LlmManager('together', 'test-model')
            llm = manager.get_llm()
            assert llm is mock_chat_together.return_value

    def test_get_llm_model_name(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test get_llm_model_name method"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            manager = LlmManager('together', 'test-model')
            model_name = manager.get_llm_model_name()
            assert model_name == 'test-model'


# API Key Management Tests
class TestLlmManagerAPIKeys:
    """Tests for LlmManager API key handling"""

    def test_together_api_key_from_config(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test using Together API key from config"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            LlmManager('together', 'test-model')
            
            # Should use API key from config
            mock_config.get_together_api_key.assert_called_once()
            # Should not prompt user
            mock_getpass.assert_not_called()

    def test_together_api_key_from_env(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test using Together API key from environment variable"""
        # Set empty API key in config
        mock_config.get_together_api_key.return_value = ""
        
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch.dict('os.environ', {'TOGETHER_API_KEY': 'env_api_key'}):
            
            LlmManager('together', 'test-model')
            
            # Should check config but not prompt user
            mock_config.get_together_api_key.assert_called_once()
            mock_getpass.assert_not_called()

    def test_together_api_key_from_user_input(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test getting Together API key from user input if not in config or env"""
        # Set empty API key in config
        mock_config.get_together_api_key.return_value = ""
        
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch.dict('os.environ', {}, clear=True):
            
            LlmManager('together', 'test-model')
            
            # Should check config and prompt user
            mock_config.get_together_api_key.assert_called_once()
            mock_getpass.assert_called_once()

    def test_openai_api_key_from_config(self, mock_config, mock_getpass, mock_logging, mock_chat_openai):
        """Test using OpenAI API key from config"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            LlmManager('gpt', 'test-model')
            
            # Should use API key from config
            mock_config.get_openai_api_key.assert_called_once()
            # Should not prompt user
            mock_getpass.assert_not_called()

    def test_openai_api_key_from_env(self, mock_config, mock_getpass, mock_logging, mock_chat_openai):
        """Test using OpenAI API key from environment variable"""
        # Set empty API key in config
        mock_config.get_openai_api_key.return_value = ""
        
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch.dict('os.environ', {'OPENAI_API_KEY': 'env_api_key'}):
            
            LlmManager('gpt', 'test-model')
            
            # Should check config but not prompt user
            mock_config.get_openai_api_key.assert_called_once()
            mock_getpass.assert_not_called()

    def test_openai_api_key_from_user_input(self, mock_config, mock_getpass, mock_logging, mock_chat_openai):
        """Test getting OpenAI API key from user input if not in config or env"""
        # Set empty API key in config
        mock_config.get_openai_api_key.return_value = ""
        
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch.dict('os.environ', {}, clear=True):
            
            LlmManager('gpt', 'test-model')
            
            # Should check config and prompt user
            mock_config.get_openai_api_key.assert_called_once()
            mock_getpass.assert_called_once()


# Constructor Parameter Tests
class TestLlmManagerParameters:
    """Tests for LlmManager constructor parameters"""

    def test_together_with_temperature(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test setting temperature for Together API"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            # Set custom temperature
            LlmManager('together', 'test-model', temperature=0.5)
            
            # Check ChatTogether was called with right temperature
            mock_chat_together.assert_called_once()
            args, kwargs = mock_chat_together.call_args
            assert kwargs['temperature'] == 0.5

    def test_openai_with_temperature(self, mock_config, mock_getpass, mock_logging, mock_chat_openai):
        """Test setting temperature for OpenAI API"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            # Set custom temperature
            LlmManager('gpt', 'test-model', temperature=0.3)
            
            # Check ChatOpenAI was called with right temperature
            mock_chat_openai.assert_called_once()
            args, kwargs = mock_chat_openai.call_args
            assert kwargs['temperature'] == 0.3

    def test_default_temperature(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test default temperature value"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            # Use default temperature
            LlmManager('together', 'test-model')
            
            # Check ChatTogether was called with default temperature
            mock_chat_together.assert_called_once()
            args, kwargs = mock_chat_together.call_args
            assert kwargs['temperature'] == 0.7  # Default value in LlmManager


# Functional Tests with mocked API responses
class TestLlmManagerFunctional:
    """Functional tests for LlmManager"""

    def test_together_model_creation(self, mock_config, mock_getpass, mock_logging):
        """Test that TogetherAI model is created correctly"""
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch('src.LlmManager.ChatTogether') as mock_chat_together:
            
            mock_chat_together.return_value = MagicMock()
            
            manager = LlmManager('together', 'claude-3-opus')
            
            # Check that ChatTogether was called with correct parameters
            mock_chat_together.assert_called_once_with(
                model='claude-3-opus',
                temperature=0.7,
                max_tokens=None,
                timeout=None,
                max_retries=2
            )

    def test_openai_model_creation(self, mock_config, mock_getpass, mock_logging):
        """Test that OpenAI model is created correctly"""
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch('src.LlmManager.ChatOpenAI') as mock_chat_openai:
            
            mock_chat_openai.return_value = MagicMock()
            
            manager = LlmManager('gpt', 'gpt-4-turbo')
            
            # Check that ChatOpenAI was called with correct parameters
            mock_chat_openai.assert_called_once_with(temperature=0.7)


# Optional real API tests that can be skipped with -m "not realapi"
class TestLlmManagerRealAPI:
    """Tests using real API calls (optional, can be skipped)"""

    @realapi
    def test_together_real_init(self, real_config):
        """Test initialization with real Together API"""
        api_key = real_config.get_together_api_key()
        model_name = real_config.get_llm_model_name()
        
        # Skip if no API key
        if not api_key:
            pytest.skip("No Together API key configured for real API test")
        
        # Create real LlmManager
        manager = LlmManager('together', model_name)
        
        # Check model creation
        assert manager.llm is not None
        assert isinstance(manager.llm, ChatTogether)
        assert manager.get_llm_model_name() == model_name

    @realapi
    def test_openai_real_init(self, real_config):
        """Test initialization with real OpenAI API"""
        api_key = real_config.get_openai_api_key()
        
        # Skip if no API key
        if not api_key:
            pytest.skip("No OpenAI API key configured for real API test")
        
        # Create real LlmManager
        manager = LlmManager('gpt', 'gpt-3.5-turbo')
        
        # Check model creation
        assert manager.llm is not None
        assert isinstance(manager.llm, ChatOpenAI)
        assert manager.get_llm_model_name() == 'gpt-3.5-turbo'


# Edge Case and Error Handling Tests
class TestLlmManagerEdgeCases:
    """Tests for edge cases and error handling in LlmManager"""

    def test_none_model_name_assertion(self, mock_config, mock_getpass, mock_logging):
        """Test assertion when model name is None and not in config"""
        # Make config return None for model name
        mock_config.get_llm_model_name.return_value = None
        
        with patch('src.LlmManager.Config', return_value=mock_config):
            # Should raise assertion error
            with pytest.raises(AssertionError) as exc_info:
                LlmManager('together', None)
            
            assert "Model name must be specified" in str(exc_info.value)

    def test_empty_model_name(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test with empty string model name"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            # Empty string is not None so should work
            manager = LlmManager('together', "")
            
            # Should have empty string as model name
            assert manager.get_llm_model_name() == ""

    def test_error_handling_in_together_init(self, mock_config, mock_getpass, mock_logging):
        """Test error handling when ChatTogether raises exception"""
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch('src.LlmManager.ChatTogether', side_effect=ValueError("Model initialization error")):
            
            # Should propagate the error
            with pytest.raises(ValueError) as exc_info:
                LlmManager('together', 'test-model')
            
            assert "Model initialization error" in str(exc_info.value)

    def test_error_handling_in_openai_init(self, mock_config, mock_getpass, mock_logging):
        """Test error handling when ChatOpenAI raises exception"""
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch('src.LlmManager.ChatOpenAI', side_effect=ValueError("Model initialization error")):
            
            # Should propagate the error
            with pytest.raises(ValueError) as exc_info:
                LlmManager('gpt', 'test-model')
            
            assert "Model initialization error" in str(exc_info.value)


# Integration Tests
class TestLlmManagerIntegration:
    """Integration tests for LlmManager with other components"""

    def test_with_coordinates_inference(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test integration with CoordinatesInference mock"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            manager = LlmManager('together', 'test-model')
            
            # Create mock CoordinatesInference
            mock_coords_inference = MagicMock()
            
            # Use LlmManager's llm with CoordinatesInference
            mock_coords_inference.extract_coordinates_from_text.return_value = ["NM_000546.5:c.215C>G"]
            
            # Pass LLM to mock CoordinatesInference constructor
            mock_coords_inference_class = MagicMock(return_value=mock_coords_inference)
            mock_coords_inference_class(manager.get_llm())
            
            # Check that LLM was passed correctly
            mock_coords_inference_class.assert_called_once_with(manager.get_llm())

    def test_with_llm_context_analyzer(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test integration with LlmContextAnalyzer mock"""
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch('src.LlmManager.LlmManager') as mock_llm_manager_class:
            
            # Create mock LlmManager that returns our mock ChatTogether
            mock_llm_manager = MagicMock()
            mock_llm_manager.get_llm.return_value = mock_chat_together.return_value
            mock_llm_manager_class.return_value = mock_llm_manager
            
            # Create mock LlmContextAnalyzer
            mock_analyzer = MagicMock()
            
            # Create mock LlmContextAnalyzer class
            mock_analyzer_class = MagicMock(return_value=mock_analyzer)
            
            # Simulate LlmContextAnalyzer creating LlmManager
            mock_analyzer_class(llm_model_name='test-model')
            
            # Check LlmManager was created as expected
            mock_llm_manager_class.assert_called_once_with('together', 'test-model')


# Additional Tests
class TestLlmManagerAdditional:
    """Additional tests for LlmManager"""

    def test_environment_variable_precedence(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test that environment variable takes precedence over user prompt"""
        # Set empty API key in config
        mock_config.get_together_api_key.return_value = ""
        
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch.dict('os.environ', {'TOGETHER_API_KEY': 'env_api_key'}):
            
            LlmManager('together', 'test-model')
            
            # Should not prompt user when env var exists
            mock_getpass.assert_not_called()

    def test_config_precedence(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test that config takes precedence over environment variable"""
        # Set API key in config
        mock_config.get_together_api_key.return_value = "config_api_key"
        
        with patch('src.LlmManager.Config', return_value=mock_config), \
             patch.dict('os.environ', {'TOGETHER_API_KEY': 'env_api_key'}), \
             patch.object(os.environ, 'get') as mock_env_get:
            
            LlmManager('together', 'test-model')
            
            # Should not check env when config has key
            mock_env_get.assert_not_called()
            # Should not prompt user
            mock_getpass.assert_not_called()

    def test_logging_calls(self, mock_config, mock_getpass, mock_logging, mock_chat_together):
        """Test that appropriate logging calls are made"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            LlmManager('together', 'test-model')
            
            # Should log model loading
            mock_logging.info.assert_called_with('Loaded TogetherAI model: test-model')

    def test_multiple_instances(self, mock_config, mock_getpass, mock_logging, mock_chat_together, mock_chat_openai):
        """Test creating multiple LlmManager instances"""
        with patch('src.LlmManager.Config', return_value=mock_config):
            manager1 = LlmManager('together', 'model1')
            manager2 = LlmManager('gpt', 'model2')
            
            # Each should have correct endpoint and model
            assert manager1.llm is mock_chat_together.return_value
            assert manager1.llm_model_name == 'model1'
            
            assert manager2.llm is mock_chat_openai.return_value
            assert manager2.llm_model_name == 'model2' 