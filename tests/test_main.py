"""
Tests for main application module.
"""
import pytest
from unittest.mock import patch, MagicMock, call
from src.main import main

# Użyjemy dekoratorów patch, aby zastąpić wszystkie zależności na poziomie najniższym
@patch('src.utils.llm.manager.ChatOpenAI')  # Mockujemy klasę ChatOpenAI
@patch('src.utils.logging.get_logger')
@patch('src.utils.llm.manager.LlmManager')
@patch('src.utils.config.config.Config')
def test_main_success(mock_config_class, mock_llm_manager_class, mock_get_logger, mock_chat_openai):
    """Test successful main execution."""
    # Konfiguracja mocków
    mock_config_instance = MagicMock()
    mock_config_instance.get_openai_api_key.return_value = "mock-api-key"
    mock_config_class.return_value = mock_config_instance
    
    # Konfiguracja mock LlmManager
    mock_llm_instance = MagicMock()
    mock_llm_manager_class.return_value = mock_llm_instance
    
    # Konfiguracja loggera
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    
    # Wykonanie funkcji main
    main()
    
    # Sprawdzenie, czy Config został utworzony
    mock_config_class.assert_called_once()
    
    # Sprawdzenie, czy LlmManager został utworzony z prawidłowymi parametrami
    mock_llm_manager_class.assert_called_once_with(
        provider='openai',
        temperature=0.7
    )
    
    # Sprawdzenie wywołania logów
    mock_logger.info.assert_any_call('Configuration loaded successfully')
    mock_logger.info.assert_any_call('LLM manager initialized successfully')
    mock_logger.error.assert_not_called()

@patch('src.utils.logging.get_logger')
@patch('src.utils.llm.manager.ChatOpenAI')
@patch('src.utils.llm.manager.LlmManager')
@patch('src.utils.config.config.Config')
def test_main_config_error(mock_config_class, mock_llm_manager_class, mock_chat_openai, mock_get_logger):
    """Test main execution with config error."""
    # Symulowanie wyjątku przy tworzeniu Config
    mock_config_class.side_effect = Exception('Config error')
    
    # Konfiguracja mock loggera
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    
    # Upewniamy się, że LlmManager nie jest nawet wywoływany, bo wyjątek pojawia się wcześniej
    mock_llm_manager_class.reset_mock()
    
    # Sprawdzenie, czy wyjątek jest propagowany
    with pytest.raises(Exception) as excinfo:
        main()
    
    # Sprawdzenie wyjątku
    assert str(excinfo.value) == 'Config error'
    
    # Sprawdzenie, że LlmManager nie był wywołany
    mock_llm_manager_class.assert_not_called()
    
    # Sprawdzenie logów błędu
    mock_logger.error.assert_called_once_with('Application error: Config error')

@patch('src.utils.logging.get_logger')
@patch('src.utils.llm.manager.ChatOpenAI')
@patch('src.utils.llm.manager.LlmManager')
@patch('src.utils.config.config.Config')
def test_main_llm_error(mock_config_class, mock_llm_manager_class, mock_chat_openai, mock_get_logger):
    """Test main execution with LLM error."""
    # Konfiguracja mocków Config
    mock_config_instance = MagicMock()
    mock_config_instance.get_openai_api_key.return_value = "mock-api-key"
    mock_config_class.return_value = mock_config_instance
    
    # Symulowanie wyjątku przy tworzeniu LlmManager
    mock_llm_manager_class.side_effect = Exception('LLM error')
    
    # Konfiguracja mock loggera
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    
    # Sprawdzenie, czy wyjątek jest propagowany
    with pytest.raises(Exception) as excinfo:
        main()
    
    # Sprawdzenie wyjątku
    assert str(excinfo.value) == 'LLM error'
    
    # Sprawdzenie logów błędu
    mock_logger.error.assert_called_once_with('Application error: LLM error') 