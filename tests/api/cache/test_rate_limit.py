"""
Testy dla mechanizmu ograniczania częstotliwości zapytań API.

Ten moduł zawiera testy sprawdzające, czy klienty API (ClinVarClient i PubTatorClient)
prawidłowo ograniczają częstotliwość zapytań zgodnie z wymaganiami odpowiednich API.
"""

import time
import pytest
from unittest.mock import patch, MagicMock, Mock

import requests

from src.api.clients.clinvar_client import ClinVarClient
from src.api.clients.pubtator_client import PubTatorClient


def create_mock_response(status_code=200, json_data=None, text=None):
    """Tworzy obiekt imitujący odpowiedź HTTP dla testów."""
    mock_resp = Mock()
    mock_resp.status_code = status_code
    
    if json_data is not None:
        mock_resp.json = MagicMock(return_value=json_data)
    
    if text is not None:
        mock_resp.text = text
    
    mock_resp.content = b"{}"
    mock_resp.headers = {}
    
    return mock_resp


@patch('requests.get')
def test_clinvar_client_rate_limit_without_api_key(mock_get):
    """Test sprawdzający, czy ClinVarClient prawidłowo ogranicza zapytania do 3 na sekundę (bez klucza API)."""
    # Tworzymy klienta bez klucza API
    client = ClinVarClient(email="test@example.com", use_cache=False)
    
    # Konfiguracja mocka
    mock_get.return_value = create_mock_response(
        json_data={"id": "test_id", "name": "test_variant"}
    )
    
    # Zapisujemy czas rozpoczęcia
    start_time = time.time()
    
    # Wykonujemy 10 zapytań
    for i in range(10):
        client._make_request("einfo", method="GET", params={"db": "clinvar"})
    
    # Mierzmy czas wykonania
    elapsed_time = time.time() - start_time
    
    # Bez limitu 10 zapytań powinno trwać mniej niż 1 sekunda
    # Z limitem 3 req/s (interwał 0.34s) powinno trwać co najmniej 3 sekundy
    # 10 zapytań * 0.34s = 3.4s (teoretyczny minimalny czas)
    # Dodajemy margines bezpieczeństwa, więc powinno trwać >= 3s
    assert elapsed_time >= 3.0, f"Zapytania wykonane zbyt szybko: {elapsed_time}s. Oczekiwano >= 3.0s"
    
    # Sprawdzamy, czy wykonano 10 zapytań
    assert mock_get.call_count == 10


@patch('requests.get')
def test_clinvar_client_rate_limit_with_api_key(mock_get):
    """Test sprawdzający, czy ClinVarClient prawidłowo ogranicza zapytania do 10 na sekundę (z kluczem API)."""
    # Tworzymy klienta z kluczem API
    client = ClinVarClient(
        email="test@example.com", 
        api_key="TESTKEY12345", 
        use_cache=False
    )
    
    # Konfiguracja mocka
    mock_get.return_value = create_mock_response(
        json_data={"id": "test_id", "name": "test_variant"}
    )
    
    # Zapisujemy czas rozpoczęcia
    start_time = time.time()
    
    # Wykonujemy 20 zapytań
    for i in range(20):
        client._make_request("einfo", method="GET", params={"db": "clinvar"})
    
    # Mierzmy czas wykonania
    elapsed_time = time.time() - start_time
    
    # Z limitem 10 req/s (interwał 0.11s) 20 zapytań powinno trwać co najmniej 2 sekundy
    # 20 zapytań * 0.11s = 2.2s (teoretyczny minimalny czas)
    # Dodajemy margines bezpieczeństwa, więc powinno trwać >= 2s
    assert elapsed_time >= 2.0, f"Zapytania wykonane zbyt szybko: {elapsed_time}s. Oczekiwano >= 2.0s"
    
    # Sprawdzamy, czy wykonano 20 zapytań
    assert mock_get.call_count == 20


@patch('requests.get')
def test_pubtator_client_rate_limit(mock_get):
    """Test sprawdzający, czy PubTatorClient prawidłowo ogranicza zapytania do 20 na sekundę."""
    # Tworzymy klienta
    client = PubTatorClient(use_cache=False)
    
    # Konfiguracja mocka
    mock_get.return_value = create_mock_response(
        json_data={"documents": []}
    )
    
    # Zapisujemy czas rozpoczęcia
    start_time = time.time()
    
    # Wykonujemy 40 zapytań
    for i in range(40):
        client._make_request("publications", method="GET", params={"pmids": "12345"})
    
    # Mierzmy czas wykonania
    elapsed_time = time.time() - start_time
    
    # Z limitem 20 req/s (interwał 0.05s) 40 zapytań powinno trwać co najmniej 2 sekundy
    # 40 zapytań * 0.05s = 2.0s (teoretyczny minimalny czas)
    # Dodajemy margines bezpieczeństwa, więc powinno trwać >= 2s
    assert elapsed_time >= 2.0, f"Zapytania wykonane zbyt szybko: {elapsed_time}s. Oczekiwano >= 2.0s"
    
    # Sprawdzamy, czy wykonano 40 zapytań
    assert mock_get.call_count == 40


@patch('requests.get')
def test_clinvar_cache_bypasses_rate_limit(mock_get):
    """Test sprawdzający, czy cache w ClinVarClient pozwala ominąć ograniczenia częstotliwości zapytań."""
    # Tworzymy klienta z włączonym cache'em
    client = ClinVarClient(email="test@example.com", use_cache=True)
    
    # Konfiguracja mocka
    mock_get.return_value = create_mock_response(
        json_data={"id": "test_id", "name": "test_variant"}
    )
    
    # Zapisujemy czas rozpoczęcia
    start_time = time.time()
    
    # Wykonujemy to samo zapytanie 10 razy (powinno być cache'owane)
    for i in range(10):
        client._make_request("einfo", method="GET", params={"db": "clinvar"})
    
    # Mierzmy czas wykonania
    elapsed_time = time.time() - start_time
    
    # Pierwsze zapytanie trafi do API, reszta powinna być pobrana z cache'a
    # Więc cały proces powinien być szybki - znacznie poniżej 3 sekund
    # (które są wymagane dla 10 zapytań z limitem 3 req/s)
    assert elapsed_time < 0.5, f"Cache nie przyspiesza zapytań: {elapsed_time}s. Oczekiwano < 0.5s"
    
    # Powinno być wykonane tylko jedno faktyczne zapytanie HTTP
    assert mock_get.call_count == 1


@patch('requests.get')
def test_pubtator_cache_bypasses_rate_limit(mock_get):
    """Test sprawdzający, czy cache w PubTatorClient pozwala ominąć ograniczenia częstotliwości zapytań."""
    # Tworzymy klienta z włączonym cache'em
    client = PubTatorClient(use_cache=True)
    
    # Konfiguracja mocka
    mock_get.return_value = create_mock_response(
        json_data={"documents": []}
    )
    
    # Zapisujemy czas rozpoczęcia
    start_time = time.time()
    
    # Wykonujemy to samo zapytanie 20 razy (powinno być cache'owane)
    for i in range(20):
        client._make_request("publications", method="GET", params={"pmids": "12345"})
    
    # Mierzmy czas wykonania
    elapsed_time = time.time() - start_time
    
    # Pierwsze zapytanie trafi do API, reszta powinna być pobrana z cache'a
    # Oczekujemy, że czas będzie znacznie krótszy niż 20 zapytań po kolei
    # Ale zwiększamy limit na czas wykonania, aby test był bardziej stabilny
    assert elapsed_time < 1.5, f"Cache nie przyspiesza zapytań: {elapsed_time}s. Oczekiwano < 1.5s"
    
    # Sprawdzamy, czy mock został wywołany tylko raz (pierwsze zapytanie)
    assert mock_get.call_count == 1, f"Mock został wywołany {mock_get.call_count} razy, oczekiwano 1" 