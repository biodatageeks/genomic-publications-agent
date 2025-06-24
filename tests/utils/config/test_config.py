"""
Tests for config module.
"""
import os
import pytest
import yaml
from unittest.mock import patch, mock_open
from src.utils.config.config import Config

@pytest.fixture
def mock_yaml():
    """Mock YAML data."""
    return {
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

@pytest.fixture
def mock_config_file(mock_yaml):
    """Mock config file."""
    with patch('builtins.open', mock_open(read_data=yaml.dump(mock_yaml))):
        yield

@pytest.fixture
def mock_json():
    """Mock JSON data."""
    return {
        'examples': ['chr1:100-200', 'chr2:300-400'],
        'patterns': ['chr\\d+:\\d+-\\d+']
    }

@pytest.fixture
def mock_json_file(mock_json):
    """Mock JSON file."""
    with patch('builtins.open', mock_open(read_data=str(mock_json))):
        yield

def test_load_config(mock_config_file):
    """Test loading config from file."""
    config = Config()
    assert config.config['llm']['model_name'] == 'test-model'

def test_get_llm_model_name(mock_config_file):
    """Test getting LLM model name."""
    config = Config()
    assert config.get_llm_model_name() == 'test-model'

def test_get_openai_api_key(mock_config_file):
    """Test getting OpenAI API key."""
    config = Config()
    assert config.get_openai_api_key() == 'test-openai-key'

def test_get_together_api_key(mock_config_file):
    """Test getting Together API key."""
    config = Config()
    assert config.get_together_api_key() == 'test-together-key'

def test_get_contact_email(mock_config_file):
    """Test getting contact email."""
    config = Config()
    assert config.get_contact_email() == 'test@example.com'

def test_load_genomic_coordinates_examples(mock_config_file, mock_json_file):
    """Test loading genomic coordinates examples."""
    config = Config()
    examples = config.load_genomic_coordinates_examples()
    assert examples == {'examples': ['chr1:100-200', 'chr2:300-400']}

def test_load_coordinates_regexes(mock_config_file, mock_json_file):
    """Test loading coordinates regexes."""
    config = Config()
    regexes = config.load_coordinates_regexes()
    assert regexes == {'patterns': ['chr\\d+:\\d+-\\d+']}

def test_config_file_not_found():
    """Test handling missing config file."""
    with patch('builtins.open', side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            Config() 