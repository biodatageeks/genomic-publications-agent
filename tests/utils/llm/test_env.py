"""
Tests for LLM environment configuration.
"""
import os
import pytest
from unittest.mock import patch
from src.utils.llm import LlmManager

def test_openai_api_key():
    """Test OpenAI API key configuration."""
    # Set environment variable
    os.environ['OPENAI_API_KEY'] = 'test-key'
    
    try:
        # Initialize LLM manager
        manager = LlmManager(endpoint='gpt')
        
        # Verify API key was used
        assert os.environ['OPENAI_API_KEY'] == 'test-key'
    finally:
        # Cleanup
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']

def test_together_api_key():
    """Test Together API key configuration."""
    # Set environment variable
    os.environ['TOGETHER_API_KEY'] = 'test-key'
    
    try:
        # Initialize LLM manager
        manager = LlmManager(endpoint='together')
        
        # Verify API key was used
        assert os.environ['TOGETHER_API_KEY'] == 'test-key'
    finally:
        # Cleanup
        if 'TOGETHER_API_KEY' in os.environ:
            del os.environ['TOGETHER_API_KEY']

def test_missing_api_key():
    """Test handling missing API key."""
    # Remove environment variables
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    if 'TOGETHER_API_KEY' in os.environ:
        del os.environ['TOGETHER_API_KEY']
    
    # Mock getpass
    with patch('getpass.getpass', return_value='test-key'):
        # Initialize LLM manager
        manager = LlmManager(endpoint='gpt')
        
        # Verify API key was set
        assert os.environ['OPENAI_API_KEY'] == 'test-key'

def test_invalid_endpoint():
    """Test handling invalid endpoint."""
    with pytest.raises(ValueError, match='Invalid LLM endpoint: invalid'):
        LlmManager(endpoint='invalid')

def test_custom_temperature():
    """Test custom temperature setting."""
    manager = LlmManager(endpoint='gpt', temperature=0.5)
    assert manager.llm.temperature == 0.5

def test_custom_model_name():
    """Test custom model name setting."""
    manager = LlmManager(endpoint='gpt', llm_model_name='custom-model')
    assert manager.llm_model_name == 'custom-model' 