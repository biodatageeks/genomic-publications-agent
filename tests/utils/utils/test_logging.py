"""
Tests for logging module.
"""
import logging
import os
import pytest
from unittest.mock import patch
from src.utils.logging import get_logger

@pytest.fixture
def mock_logging():
    """Mock logging module."""
    with patch('src.core.utils.logging.logging') as mock:
        yield mock

def test_get_logger_default_level(mock_logging):
    """Test getting logger with default level."""
    logger = get_logger('test')
    assert logger.level == logging.INFO

def test_get_logger_custom_level(mock_logging):
    """Test getting logger with custom level."""
    logger = get_logger('test', level=logging.DEBUG)
    assert logger.level == logging.DEBUG

def test_get_logger_handlers(mock_logging):
    """Test logger handlers."""
    logger = get_logger('test')
    assert len(logger.handlers) >= 1  # At least console handler

def test_get_logger_file_handler(mock_logging):
    """Test file handler creation."""
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    try:
        logger = get_logger('test')
        file_handlers = [
            h for h in logger.handlers 
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1
        assert file_handlers[0].baseFilename.endswith('test.log')
    finally:
        # Cleanup
        if os.path.exists('logs/test.log'):
            os.remove('logs/test.log')
        if os.path.exists('logs'):
            os.rmdir('logs') 