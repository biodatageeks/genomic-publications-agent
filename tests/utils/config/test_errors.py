"""
Tests for configuration error handling.
"""
import pytest
from unittest.mock import patch
from src.utils.config.config import Config

def test_file_not_found_error():
    """Test handling file not found error."""
    with patch('builtins.open', side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            Config()

def test_permission_error():
    """Test handling permission error."""
    with patch('builtins.open', side_effect=PermissionError):
        with pytest.raises(PermissionError):
            Config()

def test_yaml_error():
    """Test handling YAML error."""
    with patch('yaml.safe_load', side_effect=Exception('Invalid YAML')):
        with pytest.raises(Exception, match='Invalid YAML'):
            Config()

def test_json_error():
    """Test handling JSON error."""
    with patch('json.load', side_effect=Exception('Invalid JSON')):
        with pytest.raises(Exception, match='Invalid JSON'):
            Config()

def test_missing_required_field_error():
    """Test handling missing required field error."""
    config_data = {
        'llm': {
            'model_name': 'test-model'
        }
        # Missing required fields
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        with pytest.raises(KeyError):
            Config()

def test_invalid_value_error():
    """Test handling invalid value error."""
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

def test_invalid_type_error():
    """Test handling invalid type error."""
    config_data = {
        'llm': {
            'model_name': 123  # Invalid type
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
        with pytest.raises(TypeError):
            Config()

def test_invalid_path_error():
    """Test handling invalid path error."""
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
            'genomic_coordinates_examples': '/invalid/path',  # Invalid path
            'coordinates_regexes': 'data/regexes.json'
        }
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        with pytest.raises(ValueError, match='Invalid path'):
            Config() 