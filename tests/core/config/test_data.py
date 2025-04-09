"""
Tests for configuration data handling.
"""
import os
import pytest
from unittest.mock import patch
from src.core.config.config import Config

def test_raw_data_dir():
    """Test raw data directory setting."""
    config = Config()
    assert os.path.isdir(config.config['data']['raw_dir'])

def test_processed_data_dir():
    """Test processed data directory setting."""
    config = Config()
    assert os.path.isdir(config.config['data']['processed_dir'])

def test_max_file_size():
    """Test maximum file size setting."""
    config = Config()
    assert isinstance(config.config['data']['max_file_size'], int)
    assert config.config['data']['max_file_size'] > 0

def test_data_permissions():
    """Test data directory permissions."""
    config = Config()
    raw_dir = config.config['data']['raw_dir']
    processed_dir = config.config['data']['processed_dir']
    
    # Verify directories are writable
    assert os.access(raw_dir, os.W_OK)
    assert os.access(processed_dir, os.W_OK)
    
    # Verify directories are readable
    assert os.access(raw_dir, os.R_OK)
    assert os.access(processed_dir, os.R_OK)
    
    # Verify directories are executable
    assert os.access(raw_dir, os.X_OK)
    assert os.access(processed_dir, os.X_OK)

def test_data_file_creation():
    """Test data file creation."""
    config = Config()
    raw_dir = config.config['data']['raw_dir']
    
    # Create test file
    test_file = os.path.join(raw_dir, 'test.txt')
    with open(test_file, 'w') as f:
        f.write('test')
    
    try:
        # Verify file exists
        assert os.path.exists(test_file)
        
        # Verify file size
        size = os.path.getsize(test_file)
        assert size > 0
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)

def test_data_file_size_limit():
    """Test data file size limit."""
    config = Config()
    raw_dir = config.config['data']['raw_dir']
    max_size = config.config['data']['max_file_size']
    
    # Create large test file
    test_file = os.path.join(raw_dir, 'large.txt')
    with open(test_file, 'w') as f:
        f.write('x' * (max_size + 1))
    
    try:
        # Verify file exists
        assert os.path.exists(test_file)
        
        # Verify file size exceeds limit
        size = os.path.getsize(test_file)
        assert size > max_size
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)

def test_data_file_concurrent_access():
    """Test concurrent data file access."""
    config = Config()
    raw_dir = config.config['data']['raw_dir']
    
    # Create test file
    test_file = os.path.join(raw_dir, 'test.txt')
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

def test_data_file_extension():
    """Test data file extension."""
    config = Config()
    raw_dir = config.config['data']['raw_dir']
    
    # Create test files with different extensions
    extensions = ['.txt', '.json', '.csv', '.tsv']
    test_files = []
    
    try:
        for ext in extensions:
            test_file = os.path.join(raw_dir, f'test{ext}')
            with open(test_file, 'w') as f:
                f.write('test')
            test_files.append(test_file)
            
            # Verify file exists
            assert os.path.exists(test_file)
    finally:
        # Cleanup
        for test_file in test_files:
            if os.path.exists(test_file):
                os.remove(test_file) 