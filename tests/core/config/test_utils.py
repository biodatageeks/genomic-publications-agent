"""
Tests for configuration utilities.
"""
import os
import pytest
from unittest.mock import patch
from src.core.config.config import Config

def test_get_config_path():
    """Test getting config file path."""
    config = Config()
    assert os.path.exists(config.config_path)

def test_get_config_dir():
    """Test getting config directory."""
    config = Config()
    assert os.path.isdir(os.path.dirname(config.config_path))

def test_get_data_dir():
    """Test getting data directory."""
    config = Config()
    data_dir = os.path.dirname(config.config['data']['genomic_coordinates_examples'])
    assert os.path.isdir(data_dir)

def test_get_cache_dir():
    """Test getting cache directory."""
    config = Config()
    cache_dir = config.config['cache']['directory']
    assert os.path.isdir(cache_dir)

def test_get_log_dir():
    """Test getting log directory."""
    config = Config()
    log_dir = os.path.dirname(config.config['logging']['file'])
    assert os.path.isdir(log_dir)

def test_get_max_file_size():
    """Test getting maximum file size."""
    config = Config()
    max_size = config.config['data']['max_file_size']
    assert isinstance(max_size, int)
    assert max_size > 0

def test_get_batch_size():
    """Test getting batch size."""
    config = Config()
    batch_size = config.config['analysis']['batch_size']
    assert isinstance(batch_size, int)
    assert batch_size > 0

def test_get_max_retries():
    """Test getting maximum retries."""
    config = Config()
    max_retries = config.config['analysis']['max_retries']
    assert isinstance(max_retries, int)
    assert max_retries > 0

def test_get_timeout():
    """Test getting timeout."""
    config = Config()
    timeout = config.config['analysis']['timeout']
    assert isinstance(timeout, int)
    assert timeout > 0

def test_get_cache_expiry():
    """Test getting cache expiry."""
    config = Config()
    expiry = config.config['cache']['expiry']
    assert isinstance(expiry, int)
 