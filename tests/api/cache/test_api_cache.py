"""
Testy jednostkowe dla klas APICache, MemoryCache i DiskCache.

Ten moduł zawiera testy sprawdzające funkcjonalność klas cache'a,
w tym operacje get/set/has/delete, metody pomocnicze, dekoratory
i obsługę błędów.
"""

import os
import time
import json
import pickle
import shutil
import tempfile
import threading
import pytest
from unittest.mock import patch, MagicMock, mock_open

from src.api.cache.cache import APICache, MemoryCache, DiskCache


@pytest.fixture
def temp_dir():
    """Fixture tworząca tymczasowy katalog dla testów."""
    dir_path = tempfile.mkdtemp(prefix="test_cache_")
    yield dir_path
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


class TestAPICache:
    """Testy dla ogólnej funkcjonalności APICache."""

    def test_cache_decorator(self):
        """Test dekoratora @cached dla metod."""
        cache = MemoryCache(ttl=100)

        # Definiujemy funkcję testową z licznikiem wywołań
        call_count = 0

        @cache.cached()
        def test_func(a, b=2):
            nonlocal call_count
            call_count += 1
            return a + b

        # Pierwsze wywołanie powinno trafić do funkcji
        assert test_func(1, 2) == 3
        assert call_count == 1

        # Drugie wywołanie z tymi samymi argumentami powinno trafić do cache'a
        assert test_func(1, 2) == 3
        assert call_count == 1  # Licznik nie powinien się zwiększyć

        # Wywołanie z innymi argumentami powinno trafić do funkcji
        assert test_func(3, 4) == 7
        assert call_count == 2


class TestMemoryCache:
    """Testy dla implementacji MemoryCache."""

    def test_basic_operations(self):
        """Test podstawowych operacji: set, get, has, delete."""
        cache = MemoryCache(ttl=100)

        # Dodanie i pobranie wartości
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Sprawdzenie czy klucz istnieje
        assert cache.has("key1") is True
        assert cache.has("nonexistent") is False

        # Usunięcie klucza
        cache.delete("key1")
        assert cache.has("key1") is False
        assert cache.get("key1") is None

    def test_ttl_expiration(self):
        """Test wygasania wpisów po TTL."""
        cache = MemoryCache(ttl=1)  # 1 sekunda TTL

        cache.set("expire_soon", "value")
        assert cache.get("expire_soon") == "value"

        # Poczekaj na wygaśnięcie TTL
        time.sleep(1.1)

        # Sprawdź, czy wartość wygasła
        assert cache.get("expire_soon") is None
        assert cache.has("expire_soon") is False

    def test_clear_method(self):
        """Test metody clear usuwającej wszystkie wpisy."""
        cache = MemoryCache(ttl=100)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.has("key1") is True
        assert cache.has("key2") is True

        # Wyczyść cache
        cache.clear()

        # Sprawdź, czy wszystkie wpisy zostały usunięte
        assert cache.has("key1") is False
        assert cache.has("key2") is False

    def test_max_size_limit(self):
        """Test ograniczenia maksymalnej liczby wpisów w cache'u."""
        cache = MemoryCache(ttl=100, max_size=3)

        # Dodaj więcej wpisów niż max_size
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
            # Niewielkie opóźnienie, aby timestamp był inny
            time.sleep(0.01)

        # Powinny pozostać tylko 3 najnowsze wpisy
        assert len(cache.cache) == 3
        assert cache.has("key0") is False  # Najstarszy powinien być usunięty
        assert cache.has("key1") is False  # Drugi najstarszy powinien być usunięty
        assert cache.has("key2") is True
        assert cache.has("key3") is True
        assert cache.has("key4") is True

    def test_invalidate_by_prefix(self):
        """Test usuwania wpisów po prefiksie."""
        cache = MemoryCache(ttl=100)

        # Dodaj wpisy z różnymi prefiksami
        cache.set("prefix1_key1", "value1")
        cache.set("prefix1_key2", "value2")
        cache.set("prefix2_key1", "value3")

        # Usuń wszystkie wpisy z prefiksem "prefix1_"
        count = cache.invalidate_by_prefix("prefix1_")

        # Powinny zostać usunięte 2 wpisy
        assert count == 2
        assert cache.has("prefix1_key1") is False
        assert cache.has("prefix1_key2") is False
        assert cache.has("prefix2_key1") is True


class TestDiskCache:
    """Testy dla implementacji DiskCache."""

    def test_basic_operations(self, temp_dir):
        """Test podstawowych operacji: set, get, has, delete."""
        cache = DiskCache(ttl=100, cache_dir=temp_dir)

        # Dodanie i pobranie wartości
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Sprawdzenie czy klucz istnieje
        assert cache.has("key1") is True
        assert cache.has("nonexistent") is False

        # Usunięcie klucza
        cache.delete("key1")
        assert cache.has("key1") is False
        assert cache.get("key1") is None

    def test_ttl_expiration(self, temp_dir):
        """Test wygasania wpisów po TTL."""
        cache = DiskCache(ttl=1, cache_dir=temp_dir)  # 1 sekunda TTL

        cache.set("expire_soon", "value")
        assert cache.get("expire_soon") == "value"

        # Poczekaj na wygaśnięcie TTL
        time.sleep(1.1)

        # Sprawdź, czy wartość wygasła
        assert cache.get("expire_soon") is None
        assert cache.has("expire_soon") is False

    def test_persistence(self, temp_dir):
        """Test, czy dane są zapisywane i odczytywane z dysku między instancjami."""
        # Pierwsza instancja
        cache1 = DiskCache(ttl=100, cache_dir=temp_dir)
        cache1.set("persistent_key", "persistent_value")

        # Druga instancja wskazująca na ten sam katalog
        cache2 = DiskCache(ttl=100, cache_dir=temp_dir)
        assert cache2.get("persistent_key") == "persistent_value"

    def test_clear_method(self, temp_dir):
        """Test metody clear usuwającej wszystkie wpisy."""
        cache = DiskCache(ttl=100, cache_dir=temp_dir)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.has("key1") is True
        assert cache.has("key2") is True

        # Wyczyść cache
        cache.clear()

        # Sprawdź, czy wszystkie wpisy zostały usunięte
        assert cache.has("key1") is False
        assert cache.has("key2") is False

    def test_complex_data_types(self, temp_dir):
        """Test zapisywania i odczytywania złożonych typów danych."""
        cache = DiskCache(ttl=100, cache_dir=temp_dir)

        # Słownik
        data_dict = {"key": "value", "nested": {"a": 1, "b": 2}}
        cache.set("dict_key", data_dict)
        assert cache.get("dict_key") == data_dict

        # Lista
        data_list = [1, 2, 3, "string", {"a": 1}]
        cache.set("list_key", data_list)
        assert cache.get("list_key") == data_list

    def test_handle_nonexistent_directory(self):
        """Test zachowania przy nieistniejącym katalogu cache'a."""
        # Utwórz tymczasowy katalog
        temp_path = tempfile.mkdtemp()
        # Usuń go, aby zasymulować nieistniejący katalog
        shutil.rmtree(temp_path)

        # Instancja z nieistniejącym katalogiem powinna automatycznie utworzyć katalog
        cache = DiskCache(ttl=100, cache_dir=temp_path)
        cache.set("key", "value")

        # Sprawdź, czy katalog został utworzony i dane zapisane
        assert os.path.exists(temp_path)
        assert cache.get("key") == "value"

        # Posprzątaj
        shutil.rmtree(temp_path)

    def test_concurrent_access(self, temp_dir):
        """Test zachowania przy równoległym dostępie z wielu wątków."""
        cache = DiskCache(ttl=100, cache_dir=temp_dir)
        
        def worker_set(key, value):
            cache.set(key, value)
            
        def worker_get(key, results, index):
            results[index] = cache.get(key)
        
        # Najpierw ustaw kilka wartości równolegle
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker_set, args=(f"key{i}", f"value{i}"))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        # Następnie pobierz wartości równolegle
        results = [None] * 10
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker_get, args=(f"key{i}", results, i))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        # Sprawdź, czy wszystkie wartości zostały poprawnie pobrane
        for i in range(10):
            assert results[i] == f"value{i}"

    def test_invalidate_by_prefix(self, temp_dir):
        """Test usuwania wpisów po prefiksie."""
        cache = DiskCache(ttl=100, cache_dir=temp_dir)

        # Dodaj wpisy z różnymi prefiksami
        cache.set("prefix1_key1", "value1")
        cache.set("prefix1_key2", "value2")
        cache.set("prefix2_key1", "value3")

        # Sprawdź, czy wszystkie wpisy zostały dodane
        assert cache.has("prefix1_key1") is True
        assert cache.has("prefix1_key2") is True
        assert cache.has("prefix2_key1") is True

        # Usuń wszystkie wpisy z prefiksem "prefix1_"
        count = cache.invalidate_by_prefix("prefix1_")

        # Powinny zostać usunięte 2 wpisy
        assert count == 2
        assert cache.has("prefix1_key1") is False
        assert cache.has("prefix1_key2") is False
        assert cache.has("prefix2_key1") is True 