"""
Tests for main application module.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.main import main


@pytest.fixture
def mock_logger():
    """
    Fixture returning a mock for logger.
    """
    with patch('src.main.get_logger') as mock_get_logger:
        logger_mock = MagicMock()
        mock_get_logger.return_value = logger_mock
        yield logger_mock


@patch('src.main.LlmManager')
@patch('src.main.Config')
def test_main_success(mock_config_class, mock_llm_manager_class, mock_logger):
    """
    Test checking successful execution of main function.
    
    Expected behavior:
    - Function should log information about successful configuration loading and LLM initialization.
    - No exceptions should occur.
    """
    # Setup mocks
    mock_config_instance = MagicMock()
    mock_config_class.return_value = mock_config_instance
    
    mock_llm_instance = MagicMock()
    mock_llm_manager_class.return_value = mock_llm_instance
    
    # Call tested function
    main()
    
    # Check that Config was created
    mock_config_class.assert_called_once()
    
    # Check that LlmManager was created with correct parameters
    mock_llm_manager_class.assert_called_once_with(
        provider='openai',
        temperature=0.7
    )
    
    # Check logs
    mock_logger.info.assert_any_call('Configuration loaded successfully')
    mock_logger.info.assert_any_call('LLM manager initialized successfully')


@patch('src.main.LlmManager')
@patch('src.main.Config')
def test_main_config_error(mock_config_class, mock_llm_manager_class, mock_logger):
    """
    Test checking reaction to error during Config object creation.
    
    Expected behavior:
    - Function should log error.
    - Exception should be propagated.
    """
    # Mock for Config class that throws exception
    error_message = "Configuration error"
    mock_config_class.side_effect = ValueError(error_message)
    
    # Call tested function should throw exception
    with pytest.raises(ValueError, match=error_message):
        main()
    
    # Check logs
    mock_logger.error.assert_called_once_with(f'Application error: {error_message}')


@patch('src.main.LlmManager')
@patch('src.main.Config')
def test_main_llm_error(mock_config_class, mock_llm_manager_class, mock_logger):
    """
    Test checking reaction to error during LlmManager creation.
    
    Expected behavior:
    - Function should log error.
    - Exception should be propagated.
    """
    # Setup Config mock
    mock_config_instance = MagicMock()
    mock_config_class.return_value = mock_config_instance
    
    # Mock for LlmManager class that throws exception
    error_message = "LlmManager initialization error"
    mock_llm_manager_class.side_effect = ValueError(error_message)
    
    # Call tested function should throw exception
    with pytest.raises(ValueError, match=error_message):
        main()
    
    # Check logs
    mock_logger.error.assert_called_once_with(f'Application error: {error_message}') 