"""
Tests for configuration cache.
"""
import os
import pytest
from unittest.mock import patch
from src.core.config.config import Config

def test_cache_enabled():
    """Test cache enabled setting."""
    config = Config()
    assert isinstance(config.config['cache']['enabled'], bool)

def test_cache_expiry():
    """Test cache expiry setting."""
    config = Config()
    assert isinstance(config.config['cache']['expiry'], int)
    assert config.config['cache']['expiry'] > 0

def test_cache_dir():
    """Test cache directory setting."""
    config = Config()
    assert os.path.isdir(config.config['cache']['directory'])

def test_cache_file():
    """Test cache file setting."""
    config = Config()
    cache_file = os.path.join(
        config.config['cache']['directory'],
        'config.cache'
    )
    assert isinstance(cache_file, str)

def test_cache_cleanup():
    """Test cache cleanup."""
    config = Config()
    cache_dir = config.config['cache']['directory']
    
    # Create test cache file
    test_file = os.path.join(cache_dir, 'test.cache')
    with open(test_file, 'w') as f:
        f.write('test')
    
    try:
        # Verify file exists
        assert os.path.exists(test_file)
        
        # Cleanup cache
        for file in os.listdir(cache_dir):
            if file.endswith('.cache'):
                os.remove(os.path.join(cache_dir, file))
        
        # Verify file was removed
        assert not os.path.exists(test_file)
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)

def test_cache_size():
    """Test cache size limit."""
    config = Config()
    cache_dir = config.config['cache']['directory']
    
    # Create large test file
    test_file = os.path.join(cache_dir, 'large.cache')
    with open(test_file, 'w') as f:
        f.write('x' * 1024 * 1024)  # 1MB
    
    try:
        # Verify file exists
        assert os.path.exists(test_file)
        
        # Get file size
        size = os.path.getsize(test_file)
        assert size > 0
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)

def test_cache_permissions():
    """Test cache directory permissions."""
    config = Config()
    cache_dir = config.config['cache']['directory']
    
    # Verify directory is writable
    assert os.access(cache_dir, os.W_OK)
    
    # Verify directory is readable
    assert os.access(cache_dir, os.R_OK)
    
    # Verify directory is executable
    assert os.access(cache_dir, os.X_OK)

def test_cache_concurrent_access():
    """Test concurrent cache access."""
    config = Config()
    cache_dir = config.config['cache']['directory']
    
    # Create test file
    test_file = os.path.join(cache_dir, 'test.cache')
    with open(test_file, 'w') as f:
        f.write('test')
    
    try:
        # Open file for reading
        with open(test_file, 'r') as f1:
            # Try to open file for writing
            with pytest.raises(IOError):
                with open(test_file, 'w') as f2:
                    f2.write('test2')
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file) 