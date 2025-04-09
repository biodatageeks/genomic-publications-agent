"""
Tests for configuration validation.
"""
import pytest
from unittest.mock import patch
from src.core.config.config import Config

def test_validate_config_structure():
    """Test validating config structure."""
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

def test_validate_missing_required_fields():
    """Test validating missing required fields."""
    config_data = {
        'llm': {
            'model_name': 'test-model'
        }
        # Missing required fields
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        with pytest.raises(KeyError):
            Config()

def test_validate_invalid_model_name():
    """Test validating invalid model name."""
    config_data = {
        'llm': {
            'model_name': ''  # Empty model name
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
        with pytest.raises(ValueError, match='Model name cannot be empty'):
            Config()

def test_validate_invalid_api_keys():
    """Test validating invalid API keys."""
    config_data = {
        'llm': {
            'model_name': 'test-model'
        },
        'api_keys': {
            'openai': '',  # Empty API key
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
        with pytest.raises(ValueError, match='API key cannot be empty'):
            Config()

def test_validate_invalid_email():
    """Test validating invalid email."""
    config_data = {
        'llm': {
            'model_name': 'test-model'
        },
        'api_keys': {
            'openai': 'test-openai-key',
            'together': 'test-together-key'
        },
        'contact': {
            'email': 'invalid-email'  # Invalid email format
        },
        'data': {
            'genomic_coordinates_examples': 'data/examples.json',
            'coordinates_regexes': 'data/regexes.json'
        }
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        with pytest.raises(ValueError, match='Invalid email format'):
            Config()

def test_validate_invalid_file_paths():
    """Test validating invalid file paths."""
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
            'genomic_coordinates_examples': '',  # Empty file path
            'coordinates_regexes': 'data/regexes.json'
        }
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        with pytest.raises(ValueError, match='File path cannot be empty'):
            Config() 