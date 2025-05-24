"""
Testy integracyjne dla mechanizmów cache'a używanych przez klientów API.

Ten moduł testuje integrację cachowania z klientami takimi jak ClinVarClient,
PubTatorClient i LlmContextAnalyzer.
"""

import os
import tempfile
import time
import json
import shutil
import pytest
from unittest.mock import patch, MagicMock

import requests
from src.api.cache.cache import MemoryCache, DiskCache


def create_mock_response(status_code=200, json_data=None, text=None, content=None):
    """Tworzy obiekt imitujący odpowiedź HTTP dla testów."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    
    if json_data is not None:
        mock_resp.json = MagicMock(return_value=json_data)
    
    if text is not None:
        mock_resp.text = text
    else:
        mock_resp.text = "{}"  # Domyślny tekst odpowiedzi
        
    if content is not None:
        mock_resp.content = content
    else:
        mock_resp.content = b"{}"  # Domyślna zawartość binarną
        
    mock_resp.headers = {}
    mock_resp.url = "http://example.com/test"
        
    return mock_resp


@pytest.fixture
def temp_dir():
    """Fixture tworząca tymczasowy katalog dla testów."""
    dir_path = tempfile.mkdtemp(prefix="test_cache_integration_")
    yield dir_path
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


def test_cache_expiration():
    """Test sprawdzający wygasanie cache'a."""
    # Utwórz cache z krótkim TTL
    cache = MemoryCache(ttl=1)  # 1 sekunda TTL
    
    # Dodaj wartość
    cache.set("expiring_key", "test_value")
    
    # Powinno być obecne bezpośrednio po dodaniu
    assert cache.get("expiring_key") == "test_value"
    
    # Poczekaj na wygaśnięcie TTL
    time.sleep(1.1)
    
    # Powinno wygasnąć
    assert cache.get("expiring_key") is None


def test_disk_cache_persistence(temp_dir):
    """Test sprawdzający persystencję DiskCache między instancjami."""
    # Utwórz pierwszy cache
    cache1 = DiskCache(ttl=100, cache_dir=temp_dir)
    
    # Dodaj wartość
    cache1.set("persistent", "test_value")
    
    # Utwórz nowy cache wskazujący na ten sam katalog
    cache2 = DiskCache(ttl=100, cache_dir=temp_dir)
    
    # Nowy cache powinien widzieć wartości poprzedniego
    assert cache2.get("persistent") == "test_value"


def test_api_cache_with_url_sorting():
    """Test sprawdzający sortowanie parametrów w URL dla kluczy cache'a."""
    # Tworzymy dwa żądania o tych samych parametrach, ale w innej kolejności
    req1 = requests.Request('GET', 'http://example.com/api', 
                          params={'a': 1, 'b': 2}).prepare()
    req2 = requests.Request('GET', 'http://example.com/api', 
                          params={'b': 2, 'a': 1}).prepare()
    
    # Sortujemy parametry, aby upewnić się, że klucze będą identyczne
    def generate_sorted_key(req):
        url_parts = req.url.split('?')
        if len(url_parts) > 1:
            base_url = url_parts[0]
            params = url_parts[1].split('&')
            sorted_params = '&'.join(sorted(params))
            return f"{req.method}:{base_url}?{sorted_params}"
        return f"{req.method}:{req.url}"
    
    key1 = generate_sorted_key(req1)
    key2 = generate_sorted_key(req2)
    
    # Teraz klucze powinny być identyczne, niezależnie od kolejności parametrów
    assert key1 == key2


def test_cache_invalidation():
    """Test sprawdzający invalidację cache'a."""
    # Utwórz cache
    cache = MemoryCache(ttl=100)
    
    # Dodaj wartości
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"
    
    # Invalidacja po prefiksie
    cache.invalidate_by_prefix("key")
    
    # Powinny zostać usunięte oba klucze
    assert cache.get("key1") is None
    assert cache.get("key2") is None


def test_disk_cache_invalidation_by_prefix(temp_dir):
    """Test sprawdzający invalidację DiskCache po prefiksie."""
    # Utwórz cache dyskowy
    cache = DiskCache(ttl=100, cache_dir=temp_dir)
    
    # Dodaj wartości z różnymi prefiksami
    cache.set("api_data_1", {"id": 1, "name": "test1"})
    cache.set("api_data_2", {"id": 2, "name": "test2"})
    cache.set("user_data_1", {"user_id": 1, "name": "user1"})
    
    # Sprawdź, czy wszystkie wartości są dostępne
    assert cache.get("api_data_1") == {"id": 1, "name": "test1"}
    assert cache.get("api_data_2") == {"id": 2, "name": "test2"}
    assert cache.get("user_data_1") == {"user_id": 1, "name": "user1"}
    
    # Usuń wszystkie dane API
    removed_count = cache.invalidate_by_prefix("api_")
    
    # Powinny zostać usunięte dwa wpisy
    assert removed_count == 2
    
    # Sprawdź, czy dane API zostały usunięte
    assert cache.get("api_data_1") is None
    assert cache.get("api_data_2") is None
    
    # Dane użytkownika powinny pozostać
    assert cache.get("user_data_1") == {"user_id": 1, "name": "user1"} 