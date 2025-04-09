"""
Testy dla testowego modułu main.
"""
import unittest.mock as mock
from unittest.mock import call, patch
import pytest
from tests.resources.test_main_module import main, MockConfig, MockLlmManager, MockLogger, get_logger


@pytest.fixture
def mock_logger():
    """
    Fixture zwracający mocka dla loggera.
    """
    logger_mock = mock.MagicMock(spec=MockLogger)
    with patch('tests.resources.test_main_module.logger', logger_mock):
        with patch('tests.resources.test_main_module.get_logger', return_value=logger_mock):
            yield logger_mock


def test_main_success(mock_logger):
    """
    Test sprawdzający poprawne wykonanie funkcji main.
    
    Oczekiwane zachowanie:
    - Funkcja powinna zalogować informacje o pomyślnym załadowaniu konfiguracji i inicjalizacji LLM.
    - Nie powinno wystąpić żadne wyjątki.
    """
    # Wywołanie testowanej funkcji
    result = main()
    
    # Sprawdzenie wyniku
    assert result is True
    
    # Sprawdzenie logów
    mock_logger.info.assert_any_call('Configuration loaded successfully')
    mock_logger.info.assert_any_call('LLM manager initialized successfully')


def test_main_config_error(mock_logger):
    """
    Test sprawdzający reakcję na błąd podczas tworzenia obiektu Config.
    
    Oczekiwane zachowanie:
    - Funkcja powinna zalogować błąd.
    - Wyjątek powinien być propagowany.
    """
    # Mock dla klasy Config, który rzuca wyjątek
    error_message = "Configuration error"
    with patch('tests.resources.test_main_module.Config', side_effect=ValueError(error_message)):
        # Wywołanie testowanej funkcji powinno rzucić wyjątek
        with pytest.raises(ValueError, match=error_message):
            main()
        
        # Sprawdzenie logów
        mock_logger.error.assert_called_once_with(f'Application error: {error_message}')


def test_main_llm_error(mock_logger):
    """
    Test sprawdzający reakcję na błąd podczas tworzenia LlmManager.
    
    Oczekiwane zachowanie:
    - Funkcja powinna zalogować błąd.
    - Wyjątek powinien być propagowany.
    """
    # Mock dla klasy LlmManager, który rzuca wyjątek
    error_message = "LlmManager initialization error"
    with patch('tests.resources.test_main_module.LlmManager', side_effect=ValueError(error_message)):
        # Wywołanie testowanej funkcji powinno rzucić wyjątek
        with pytest.raises(ValueError, match=error_message):
            main()
        
        # Sprawdzenie logów
        mock_logger.error.assert_called_once_with(f'Application error: {error_message}') 