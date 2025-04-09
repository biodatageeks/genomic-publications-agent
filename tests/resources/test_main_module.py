"""
Samodzielny moduł do testowania.
"""
import logging
from typing import Optional

# Klasy mock, które będą zastępowane w testach

class MockConfig:
    """Mock klasy Config."""
    
    def get_openai_api_key(self) -> str:
        """Zwraca klucz API OpenAI."""
        return "mock-openai-key"
    
    def get_together_api_key(self) -> str:
        """Zwraca klucz API Together."""
        return "mock-together-key"
    
    def get_llm_model_name(self) -> str:
        """Zwraca nazwę modelu LLM."""
        return "mock-model"
    
    def get_contact_email(self) -> str:
        """Zwraca adres email kontaktowy."""
        return "mock@example.com"


class MockLlmManager:
    """Mock klasy LlmManager."""
    
    def __init__(self, provider: str = "openai", temperature: float = 0.0):
        """Inicjalizuje LlmManager."""
        self.provider = provider
        self.temperature = temperature


class MockLogger:
    """Mock loggera."""
    
    def info(self, message: str) -> None:
        """Zapisuje informację w logu."""
        print(f"INFO: {message}")
    
    def error(self, message: str) -> None:
        """Zapisuje błąd w logu."""
        print(f"ERROR: {message}")
    
    def debug(self, message: str) -> None:
        """Zapisuje debug w logu."""
        print(f"DEBUG: {message}")


# Zmienne globalne, które będą zastępowane w testach
Config = MockConfig
LlmManager = MockLlmManager
logger = MockLogger()


def get_logger(name: str) -> MockLogger:
    """Zwraca instancję loggera."""
    return logger


def main():
    """
    Główna funkcja aplikacji do testowania.
    """
    try:
        # Ładowanie konfiguracji
        config = Config()
        logger.info('Configuration loaded successfully')
        
        # Inicjalizacja LLM managera
        llm_manager = LlmManager(
            provider='openai',
            temperature=0.7
        )
        logger.info('LLM manager initialized successfully')
        
        # Do testowania nie potrzebujemy faktycznej logiki
        return True
        
    except Exception as e:
        logger.error(f'Application error: {str(e)}')
        raise 