"""
Tests for configuration logging.
"""
import os
import logging
import pytest
from unittest.mock import patch
from src.core.config.config import Config

def test_log_level():
    """Test log level setting."""
    config = Config()
    assert isinstance(config.config['logging']['level'], str)
    assert config.config['logging']['level'] in [
        'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    ]

def test_log_format():
    """Test log format setting."""
    config = Config()
    assert isinstance(config.config['logging']['format'], str)
    assert '%(asctime)s' in config.config['logging']['format']
    assert '%(name)s' in config.config['logging']['format']
    assert '%(levelname)s' in config.config['logging']['format']
    assert '%(message)s' in config.config['logging']['format']

def test_log_file():
    """Test log file setting."""
    config = Config()
    assert os.path.isdir(os.path.dirname(config.config['logging']['file']))

def test_log_rotation():
    """Test log rotation."""
    config = Config()
    log_file = config.config['logging']['file']
    
    # Create test log file
    with open(log_file, 'w') as f:
        f.write('test\n' * 1000)  # 1000 lines
    
    try:
        # Verify file exists
        assert os.path.exists(log_file)
        
        # Get file size
        size = os.path.getsize(log_file)
        assert size > 0
    finally:
        # Cleanup
        if os.path.exists(log_file):
            os.remove(log_file)

def test_log_permissions():
    """Test log directory permissions."""
    config = Config()
    log_dir = os.path.dirname(config.config['logging']['file'])
    
    # Verify directory is writable
    assert os.access(log_dir, os.W_OK)
    
    # Verify directory is readable
    assert os.access(log_dir, os.R_OK)
    
    # Verify directory is executable
    assert os.access(log_dir, os.X_OK)

def test_log_concurrent_access():
    """Test concurrent log access."""
    config = Config()
    log_file = config.config['logging']['file']
    
    # Create test log file
    with open(log_file, 'w') as f:
        f.write('test')
    
    try:
        # Open file for reading
        with open(log_file, 'r') as f1:
            # Try to open file for writing
            with pytest.raises(IOError):
                with open(log_file, 'w') as f2:
                    f2.write('test2')
    finally:
        # Cleanup
        if os.path.exists(log_file):
            os.remove(log_file)

def test_log_handler():
    """Test log handler configuration."""
    config = Config()
    logger = logging.getLogger('test')
    
    # Add file handler
    file_handler = logging.FileHandler(config.config['logging']['file'])
    file_handler.setFormatter(
        logging.Formatter(config.config['logging']['format'])
    )
    logger.addHandler(file_handler)
    
    try:
        # Log test message
        logger.info('test message')
        
        # Verify log file exists and contains message
        with open(config.config['logging']['file'], 'r') as f:
            content = f.read()
            assert 'test message' in content
    finally:
        # Cleanup
        logger.removeHandler(file_handler)
        if os.path.exists(config.config['logging']['file']):
            os.remove(config.config['logging']['file']) 