"""
Tests for environment logging configuration.
"""
import os
import logging
import pytest
from unittest.mock import patch
from src.utils.logging import get_logger

def test_logger_creation():
    """Test logger creation."""
    logger = get_logger('test')
    assert isinstance(logger, logging.Logger)
    assert logger.name == 'test'

def test_logger_level():
    """Test logger level setting."""
    logger = get_logger('test', level=logging.DEBUG)
    assert logger.level == logging.DEBUG

def test_logger_handlers():
    """Test logger handlers."""
    logger = get_logger('test')
    assert len(logger.handlers) >= 1  # At least console handler

def test_logger_file_handler():
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

def test_logger_format():
    """Test logger format."""
    logger = get_logger('test')
    console_handlers = [
        h for h in logger.handlers 
        if isinstance(h, logging.StreamHandler)
    ]
    assert len(console_handlers) == 1
    formatter = console_handlers[0].formatter
    assert '%(asctime)s' in formatter._fmt
    assert '%(name)s' in formatter._fmt
    assert '%(levelname)s' in formatter._fmt
    assert '%(message)s' in formatter._fmt

def test_logger_multiple_instances():
    """Test multiple logger instances."""
    logger1 = get_logger('test1')
    logger2 = get_logger('test2')
    assert logger1 is not logger2
    assert logger1.name == 'test1'
    assert logger2.name == 'test2' 