"""
Tests for environment settings configuration.
"""
import os
import pytest
from unittest.mock import patch
from src.core.config.config import Config

def test_config_loading():
    """Test configuration loading."""
    # Create temporary config file
    config_data = {
        'llm': {
            'model_name': 'test-model'
        },
        'api_keys': {
            'openai': 'test-openai-key',
            'together': 'test-together-key'
        },
        'contact': {
            'email': 'test@example.com'
        },
        'data': {
            'genomic_coordinates_examples': 'data/examples.json',
            'coordinates_regexes': 'data/regexes.json'
        }
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        config = Config()
        assert config.config == config_data

def test_missing_config_file():
    """Test handling missing config file."""
    with patch('builtins.open', side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            Config()

def test_invalid_config_file():
    """Test handling invalid config file."""
    with patch('builtins.open', patch('yaml.safe_load', side_effect=Exception)):
        with pytest.raises(Exception):
            Config()

def test_get_llm_model_name():
    """Test getting LLM model name."""
    config = Config()
    assert config.get_llm_model_name() == config.config['llm']['model_name']

def test_get_openai_api_key():
    """Test getting OpenAI API key."""
    config = Config()
    assert config.get_openai_api_key() == config.config['api_keys']['openai']

def test_get_together_api_key():
    """Test getting Together API key."""
    config = Config()
    assert config.get_together_api_key() == config.config['api_keys']['together']

def test_get_contact_email():
    """Test getting contact email."""
    config = Config()
    assert config.get_contact_email() == config.config['contact']['email']

def test_load_genomic_coordinates_examples():
    """Test loading genomic coordinates examples."""
    config = Config()
    examples = config.load_genomic_coordinates_examples()
    assert isinstance(examples, dict)

def test_load_coordinates_regexes():
    """Test loading coordinates regexes."""
    config = Config()
    regexes = config.load_coordinates_regexes()
    assert isinstance(regexes, dict) 