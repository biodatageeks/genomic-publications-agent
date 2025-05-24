"""
Tests for configuration analysis settings.
"""
import pytest
from unittest.mock import patch
from src.utils.config.config import Config

def test_batch_size():
    """Test batch size setting."""
    config = Config()
    assert isinstance(config.config['analysis']['batch_size'], int)
    assert config.config['analysis']['batch_size'] > 0

def test_max_retries():
    """Test maximum retries setting."""
    config = Config()
    assert isinstance(config.config['analysis']['max_retries'], int)
    assert config.config['analysis']['max_retries'] > 0

def test_timeout():
    """Test timeout setting."""
    config = Config()
    assert isinstance(config.config['analysis']['timeout'], int)
    assert config.config['analysis']['timeout'] > 0

def test_analysis_settings_validation():
    """Test analysis settings validation."""
    config_data = {
        'analysis': {
            'batch_size': 0,  # Invalid batch size
            'max_retries': 3,
            'timeout': 300
        }
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        with pytest.raises(ValueError, match='Batch size must be positive'):
            Config()

def test_analysis_settings_type():
    """Test analysis settings type validation."""
    config_data = {
        'analysis': {
            'batch_size': '100',  # Invalid type
            'max_retries': 3,
            'timeout': 300
        }
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        with pytest.raises(TypeError):
            Config()

def test_analysis_settings_range():
    """Test analysis settings range validation."""
    config_data = {
        'analysis': {
            'batch_size': 100,
            'max_retries': 0,  # Invalid max retries
            'timeout': 300
        }
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        with pytest.raises(ValueError, match='Max retries must be positive'):
            Config()

def test_analysis_settings_timeout():
    """Test analysis settings timeout validation."""
    config_data = {
        'analysis': {
            'batch_size': 100,
            'max_retries': 3,
            'timeout': 0  # Invalid timeout
        }
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        with pytest.raises(ValueError, match='Timeout must be positive'):
            Config()

def test_analysis_settings_combination():
    """Test analysis settings combination validation."""
    config_data = {
        'analysis': {
            'batch_size': 1000,  # Large batch size
            'max_retries': 10,   # High max retries
            'timeout': 600       # Long timeout
        }
    }
    
    with patch('builtins.open', patch('yaml.safe_load', return_value=config_data)):
        config = Config()
        assert config.config['analysis']['batch_size'] == 1000
        assert config.config['analysis']['max_retries'] == 10
        assert config.config['analysis']['timeout'] == 600 