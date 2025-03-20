import json
import os
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

from src.clinvar_client.cache import APICache, DiskCache, MemoryCache


class TestMemoryCache:
    """Testy dla cache'a w pamięci."""
    
    def test_init(self):
        """Test inicjalizacji cache'a w pamięci."""
        cache = MemoryCache(ttl=300, max_size=100)
        assert cache.ttl == 300
        assert cache.max_size == 100
        assert cache.storage_type == "memory"
        
    def test_set_get(self):
        """Test ustawiania i pobierania wartości z cache'a."""
        cache = MemoryCache(ttl=300)
        
        # Zapisanie wartości
        cache.set("key1", "value1")
        assert cache.has("key1")
        
        # Pobranie wartości
        value = cache.get("key1")
        assert value == "value1"
        
        # Pobranie nieistniejącego klucza
        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", "default") == "default"
    
    def test_expiry(self):
        """Test wygasania wpisów w cache'u."""
        # Krótki czas życia dla testu
        cache = MemoryCache(ttl=1)
        
        cache.set("key_expire", "value")
        assert cache.has("key_expire")
        
        # Odczekanie na wygaśnięcie wpisu
        time.sleep(1.1)
        
        assert not cache.has("key_expire")
        assert cache.get("key_expire") is None
    
    def test_custom_ttl(self):
        """Test niestandardowego czasu życia dla wpisu."""
        cache = MemoryCache(ttl=300)
        
        # Wpis z krótkim czasem życia
        cache.set("key_short", "value", ttl=1)
        
        # Wpis z domyślnym czasem życia
        cache.set("key_long", "value")
        
        # Odczekanie na wygaśnięcie krótkiego wpisu
        time.sleep(1.1)
        
        assert not cache.has("key_short")
        assert cache.has("key_long")
    
    def test_max_size(self):
        """Test ograniczenia rozmiaru cache'a."""
        cache = MemoryCache(ttl=300, max_size=2)
        
        # Dodanie 3 wpisów
        for i in range(3):
            cache.set(f"key{i}", f"value{i}")
            time.sleep(0.1)  # Upewniamy się, że czasy dostępu są różne
        
        # Sprawdzenie, że najstarszy wpis został usunięty
        assert not cache.has("key0")
        assert cache.has("key1")
        assert cache.has("key2")
    
    def test_delete(self):
        """Test usuwania wpisów z cache'a."""
        cache = MemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert cache.has("key1")
        assert cache.delete("key1")
        assert not cache.has("key1")
        assert cache.has("key2")
        
        # Usunięcie nieistniejącego klucza
        assert not cache.delete("nonexistent")
    
    def test_clear(self):
        """Test czyszczenia całego cache'a."""
        cache = MemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert cache.clear()
        assert not cache.has("key1")
        assert not cache.has("key2")


class TestDiskCache:
    """Testy dla cache'a na dysku."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Tworzy tymczasowy katalog dla testów cache'a."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_init(self, temp_cache_dir):
        """Test inicjalizacji cache'a na dysku."""
        cache = DiskCache(ttl=300, cache_dir=temp_cache_dir)
        assert cache.ttl == 300
        assert str(cache.cache_dir) == temp_cache_dir
        assert cache.storage_type == "disk"
    
    def test_set_get_json(self, temp_cache_dir):
        """Test zapisywania i odczytywania wartości JSON z cache'a."""
        cache = DiskCache(ttl=300, cache_dir=temp_cache_dir)
        
        test_data = {"test": "value", "number": 42}
        cache.set("json_key", test_data)
        
        # Sprawdzenie, czy pliki zostały utworzone
        data_file, meta_file = cache._get_cache_file_path("json_key")
        assert data_file.exists()
        assert meta_file.exists()
        
        # Pobranie wartości
        value = cache.get("json_key")
        assert value == test_data
    
    def test_set_get_complex(self, temp_cache_dir):
        """Test zapisywania i odczytywania złożonych obiektów z cache'a."""
        cache = DiskCache(ttl=300, cache_dir=temp_cache_dir)
        
        # Obiekt, który nie jest serializowalny do JSON
        class TestObject:
            def __init__(self, name):
                self.name = name
        
        test_data = TestObject("test_name")
        cache.set("complex_key", test_data)
        
        # Pobranie wartości
        value = cache.get("complex_key")
        assert isinstance(value, TestObject)
        assert value.name == "test_name"
    
    def test_expiry(self, temp_cache_dir):
        """Test wygasania wpisów w cache'u na dysku."""
        cache = DiskCache(ttl=1, cache_dir=temp_cache_dir)
        
        cache.set("key_expire", "value")
        assert cache.has("key_expire")
        
        # Odczekanie na wygaśnięcie wpisu
        time.sleep(1.1)
        
        assert not cache.has("key_expire")
        assert cache.get("key_expire") is None
    
    def test_delete(self, temp_cache_dir):
        """Test usuwania wpisów z cache'a na dysku."""
        cache = DiskCache(cache_dir=temp_cache_dir)
        
        cache.set("key1", "value1")
        
        # Sprawdzenie, czy pliki zostały utworzone
        data_file, meta_file = cache._get_cache_file_path("key1")
        assert data_file.exists()
        assert meta_file.exists()
        
        # Usunięcie wpisu
        assert cache.delete("key1")
        assert not data_file.exists()
        assert not meta_file.exists()
        
        # Usunięcie nieistniejącego klucza
        assert not cache.delete("nonexistent")
    
    def test_clear(self, temp_cache_dir):
        """Test czyszczenia całego cache'a na dysku."""
        cache = DiskCache(cache_dir=temp_cache_dir)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Sprawdzenie, czy pliki zostały utworzone
        files = list(Path(temp_cache_dir).glob("*.cache*"))
        assert len(files) == 4  # 2 pliki danych + 2 pliki metadanych
        
        # Czyszczenie cache'a
        assert cache.clear()
        
        # Sprawdzenie, czy pliki zostały usunięte
        files = list(Path(temp_cache_dir).glob("*.cache*"))
        assert len(files) == 0


class TestCacheDecorator:
    """Testy dla dekoratora cache'a."""
    
    def test_cached_decorator(self):
        """Test działania dekoratora @cached."""
        cache = MemoryCache()
        counter = 0
        
        @cache.cached()
        def test_function(arg1, arg2=None):
            nonlocal counter
            counter += 1
            return f"Result: {arg1}, {arg2}"
        
        # Pierwsze wywołanie - funkcja powinna zostać wykonana
        result1 = test_function("test", arg2="value")
        assert result1 == "Result: test, value"
        assert counter == 1
        
        # Drugie wywołanie z tymi samymi argumentami - wynik powinien być z cache'a
        result2 = test_function("test", arg2="value")
        assert result2 == "Result: test, value"
        assert counter == 1  # counter nie powinien się zwiększyć
        
        # Wywołanie z innymi argumentami - funkcja powinna zostać wykonana
        result3 = test_function("different", arg2="value")
        assert result3 == "Result: different, value"
        assert counter == 2
    
    def test_cached_with_key_func(self):
        """Test dekoratora @cached z własną funkcją generowania klucza."""
        cache = MemoryCache()
        counter = 0
        
        def custom_key_func(arg1, **kwargs):
            # Ignorujemy kwargs, używamy tylko arg1 jako klucza
            return f"custom:{arg1}"
        
        @cache.cached(key_func=custom_key_func)
        def test_function(arg1, arg2=None):
            nonlocal counter
            counter += 1
            return f"Result: {arg1}, {arg2}"
        
        # Pierwsze wywołanie - funkcja powinna zostać wykonana
        result1 = test_function("test", arg2="value1")
        assert result1 == "Result: test, value1"
        assert counter == 1
        
        # Drugie wywołanie z innym arg2, ale takim samym arg1
        # Powinno użyć cache'a, ponieważ nasz custom_key_func ignoruje arg2
        result2 = test_function("test", arg2="value2")
        assert result2 == "Result: test, value1"  # Uwaga: nadal value1 z cache'a!
        assert counter == 1  # counter nie powinien się zwiększyć


class TestAPIClientIntegration:
    """Testy integracji cache'a z klientem API."""
    
    def test_api_client_integration(self):
        """Test integracji cache'a z symulowanym klientem API."""
        cache = MemoryCache(ttl=300)
        
        # Symulowany klient API
        class MockAPIClient:
            def __init__(self):
                self.request_count = 0
                self.cache = cache
            
            @cache.cached()
            def fetch_data(self, endpoint, param=None):
                self.request_count += 1
                return {"endpoint": endpoint, "param": param, "result": "data"}
        
        client = MockAPIClient()
        
        # Pierwsze zapytanie - powinno wykonać rzeczywiste zapytanie
        result1 = client.fetch_data("test_endpoint", param="value")
        assert result1 == {"endpoint": "test_endpoint", "param": "value", "result": "data"}
        assert client.request_count == 1
        
        # Drugie zapytanie z tymi samymi parametrami - powinno użyć cache'a
        result2 = client.fetch_data("test_endpoint", param="value")
        assert result2 == result1
        assert client.request_count == 1  # Licznik się nie zwiększył
        
        # Zapytanie z innymi parametrami - powinno wykonać nowe zapytanie
        result3 = client.fetch_data("other_endpoint")
        assert result3 != result1
        assert client.request_count == 2 