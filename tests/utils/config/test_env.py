"""
Tests for environment configuration.
"""
import os
import pytest
from unittest.mock import patch
from dotenv import load_dotenv

def test_load_env_vars():
    """Test loading environment variables."""
    # Create temporary .env file
    with open('.env', 'w') as f:
        f.write('TEST_VAR=test_value\n')
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Verify variable was loaded
        assert os.getenv('TEST_VAR') == 'test_value'
    finally:
        # Cleanup
        if os.path.exists('.env'):
            os.remove('.env')

def test_missing_env_file():
    """Test handling missing .env file."""
    # Remove .env file if it exists
    if os.path.exists('.env'):
        os.remove('.env')
    
    # Load environment variables
    load_dotenv()
    
    # Verify no error was raised
    assert True

def test_invalid_env_file():
    """Test handling invalid .env file."""
    # Create invalid .env file
    with open('.env', 'w') as f:
        f.write('INVALID_LINE\n')
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Verify no error was raised
        assert True
    finally:
        # Cleanup
        if os.path.exists('.env'):
            os.remove('.env')

def test_env_var_priority():
    """Test environment variable priority."""
    # Set environment variable
    os.environ['TEST_VAR'] = 'system_value'
    
    # Create .env file with different value
    with open('.env', 'w') as f:
        f.write('TEST_VAR=env_value\n')
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Verify system value takes precedence
        assert os.getenv('TEST_VAR') == 'system_value'
    finally:
        # Cleanup
        if os.path.exists('.env'):
            os.remove('.env')
        # Remove environment variable
        if 'TEST_VAR' in os.environ:
            del os.environ['TEST_VAR'] 