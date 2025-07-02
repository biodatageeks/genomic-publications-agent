"""
Shared fixtures for LlmManager tests.

This module provides fixtures that can be used across different
test files for the LlmManager class.
"""

import pytest
from unittest.mock import MagicMock
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.llm import LlmManager
from src.utils.config.config import Config


@pytest.fixture
def shared_mock_config():
    """Creates a mock Config object that can be shared between test files"""
    mock = MagicMock(spec=Config)
    # Set up mock return values
    mock.get_together_api_key.return_value = "shared_mock_together_api_key"
    mock.get_openai_api_key.return_value = "shared_mock_openai_api_key"
    mock.get_llm_model_name.return_value = "shared_mock_model_name"
    mock.get_contact_email.return_value = "shared_mock_email@example.com"
    return mock


@pytest.fixture
def shared_real_config():
    """Creates a real Config object for API testing"""
    return Config()


# Define the marker for real API tests
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "realapi: mark test as using real API calls (skipped by default)"
    )


# Skip realapi tests by default
def pytest_collection_modifyitems(config, items):
    """Skip realapi tests unless explicitly requested"""
    if not config.getoption("--run-realapi", default=False):
        skip_realapi = pytest.mark.skip(reason="Need --run-realapi option to run tests that make real API calls")
        for item in items:
            if "realapi" in item.keywords:
                item.add_marker(skip_realapi)


# Add command line option to run real API tests
def pytest_addoption(parser):
    """Add command-line option for running real API tests"""
    parser.addoption(
        "--run-realapi", action="store_true", default=False, help="run tests that make real API calls"
    ) 