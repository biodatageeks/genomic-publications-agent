"""
Testy dla implementacji DiskCache.

Ten moduł zawiera testy jednostkowe dla klasy DiskCache, 
która implementuje mechanizm cache'a na dysku.
"""

import os
import json
import pickle
import tempfile
import time
import shutil
import pytest
from pathlib import Path

from src.cache.cache import DiskCache


# Klasa pomocnicza dla testów - musi być na poziomie modułu, a nie wewnątrz funkcji testowej
class NonJsonSerializable:
    def __init__(self, value):
        self.value = value
        
    def __eq__(self, other):
        if not isinstance(other, NonJsonSerializable):
            return False
        return self.value == other.value


@pytest.fixture
def disk_cache():
    """Fixture tworząca tymczasowy katalog i obiekt DiskCache dla testów."""
    # Utwórz tymczasowy katalog dla cache'a
    temp_dir = tempfile.mkdtemp(prefix="test_disk_cache_")
    cache = DiskCache(ttl=10, cache_dir=temp_dir)
    
    yield cache, temp_dir
    
    # Usuń tymczasowy katalog po testach
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

def test_init(disk_cache):
    """Test inicjalizacji DiskCache."""
    cache, temp_dir = disk_cache
    assert cache.ttl == 10
    assert str(cache.cache_dir) == temp_dir
    assert os.path.exists(temp_dir)

def test_has(disk_cache):
    """Test sprawdzania istnienia klucza w cache'u."""
    cache, _ = disk_cache
    # Klucz nie istnieje
    assert not cache.has("key")
    
    # Dodaj klucz
    cache.set("key", "value")
    assert cache.has("key")
    
    # Dodaj klucz z wygasłym TTL
    cache.set("expired_key", "value", ttl=1)
    time.sleep(1.1)  # Poczekaj, aż TTL wygaśnie
    assert not cache.has("expired_key")

def test_get(disk_cache):
    """Test pobierania wartości z cache'a."""
    cache, _ = disk_cache
    # Klucz nie istnieje
    assert cache.get("key") is None
    assert cache.get("key", "default") == "default"
    
    # Dodaj klucz
    cache.set("key", "value")
    assert cache.get("key") == "value"
    
    # Wygasły klucz
    cache.set("expired_key", "value", ttl=1)
    time.sleep(1.1)
    assert cache.get("expired_key") is None

def test_set(disk_cache):
    """Test ustawiania wartości w cache'u."""
    cache, _ = disk_cache
    # Podstawowy zapis
    assert cache.set("key", "value")
    assert cache.get("key") == "value"
    
    # Nadpisanie istniejącego klucza
    assert cache.set("key", "new_value")
    assert cache.get("key") == "new_value"
    
    # Sprawdź, czy plik został utworzony
    data_path, _ = cache._get_cache_file_path("key")
    assert os.path.exists(data_path)

def test_file_paths(disk_cache):
    """Test generowania ścieżek plików cache'a."""
    cache, _ = disk_cache
    # Prosty klucz
    key = "simple_key"
    data_path, meta_path = cache._get_cache_file_path(key)
    assert data_path.name == "simple_key.cache"
    assert meta_path.name == "simple_key.cache.meta"
    
    # Klucz ze znakami specjalnymi
    key = "special/key:with*chars?"
    data_path, meta_path = cache._get_cache_file_path(key)
    assert "/" not in data_path.name
    assert ":" not in data_path.name
    assert "*" not in data_path.name
    assert "?" not in data_path.name
    
    # Długi klucz
    key = "a" * 200
    data_path, meta_path = cache._get_cache_file_path(key)
    assert len(data_path.name) < 150  # Powinien być skrócony

def test_generate_disk_key(disk_cache):
    """Test generowania nazw plików dla kluczy cache'a."""
    cache, _ = disk_cache
    # Prosty klucz
    assert cache._generate_disk_key("simple") == "simple.cache"
    
    # Klucz ze znakami specjalnymi
    safe_key = cache._generate_disk_key("special/key:with*chars?")
    assert "/" not in safe_key
    assert ":" not in safe_key
    assert "*" not in safe_key
    assert "?" not in safe_key
    
    # Długi klucz
    long_key = "a" * 200
    safe_key = cache._generate_disk_key(long_key)
    assert len(safe_key) < 150

def test_metadata_file(disk_cache):
    """Test zawartości pliku metadanych."""
    cache, _ = disk_cache
    # Ustaw wartość w cache'u
    cache.set("meta_key", "value", ttl=100)
    
    # Sprawdź plik metadanych
    _, meta_path = cache._get_cache_file_path("meta_key")
    assert os.path.exists(meta_path)
    
    # Odczytaj i sprawdź zawartość pliku metadanych
    with open(meta_path, "r") as f:
        metadata = json.load(f)
        
    # Plik metadanych powinien zawierać znaczniki czasu
    assert "created_at" in metadata
    assert "expires_at" in metadata
    
    # Sprawdź TTL
    current_time = time.time()
    assert metadata["expires_at"] >= current_time
    assert metadata["created_at"] <= current_time
    assert metadata["expires_at"] - metadata["created_at"] == pytest.approx(100, abs=1)

def test_complex_data_json(disk_cache):
    """Test zapisywania i odczytywania złożonych danych w formacie JSON."""
    cache, _ = disk_cache
    # Słownik
    dict_data = {"key1": "value1", "key2": 123}
    cache.set("dict_key", dict_data)
    assert cache.get("dict_key") == dict_data
    
    # Lista
    list_data = [1, 2, 3, "test"]
    cache.set("list_key", list_data)
    assert cache.get("list_key") == list_data
    
    # Zagnieżdżone struktury
    nested_data = {"key1": [1, 2, {"nested": True}]}
    cache.set("nested_key", nested_data)
    assert cache.get("nested_key") == nested_data

def test_pickle_fallback(disk_cache):
    """Test zapisu danych, które nie mogą być serializowane do JSON."""
    cache, _ = disk_cache
    # Utwórz obiekt, który nie może być serializowany do JSON
    obj = NonJsonSerializable("test")
    
    # Zapisz obiekt - powinien zostać użyty pickle
    cache.set("non_json", obj)
    
    # Sprawdź, czy możemy odczytać obiekt
    retrieved = cache.get("non_json")
    assert isinstance(retrieved, NonJsonSerializable)
    assert retrieved.value == "test"

def test_binary_data(disk_cache):
    """Test zapisywania i odczytywania danych binarnych."""
    cache, _ = disk_cache
    # Dane binarne
    binary_data = b"\x00\x01\x02\x03\xff"
    
    # Zapisz dane
    cache.set("binary_key", binary_data)
    
    # Odczytaj dane
    retrieved = cache.get("binary_key")
    
    # Powinny być identyczne
    assert retrieved == binary_data

def test_ttl_override(disk_cache):
    """Test nadpisywania domyślnego TTL."""
    cache, _ = disk_cache
    # Ustaw wartość z niestandardowym TTL
    current_time = time.time()
    cache.set("custom_ttl", "value", ttl=5)
    
    # Sprawdź plik metadanych
    _, meta_path = cache._get_cache_file_path("custom_ttl")
    with open(meta_path, "r") as f:
        metadata = json.load(f)
        
    # Sprawdź TTL
    assert metadata["expires_at"] - metadata["created_at"] == pytest.approx(5, abs=1)
    
    # Sprawdź, czy wpis wygasa po oczekiwanym czasie
    time.sleep(5.1)
    assert not cache.has("custom_ttl")

def test_corrupted_metadata(disk_cache):
    """Test obsługi uszkodzonych plików metadanych."""
    cache, _ = disk_cache
    # Ustaw wartość
    cache.set("corrupted", "value")
    
    # Pobierz ścieżki plików
    _, meta_path = cache._get_cache_file_path("corrupted")
    
    # Nadpisz plik metadanych nieprawidłową zawartością
    with open(meta_path, "w") as f:
        f.write("invalid json")
        
    # has() powinno zwrócić False
    assert not cache.has("corrupted")
    
    # get() powinno zwrócić None
    assert cache.get("corrupted") is None

def test_corrupted_data_file(disk_cache):
    """Test obsługi uszkodzonych plików danych."""
    cache, _ = disk_cache
    # Ustaw wartość
    complex_data = {"key": "value", "list": [1, 2, 3]}
    cache.set("corrupted_data", complex_data)
    
    # Pobierz ścieżki plików
    data_path, _ = cache._get_cache_file_path("corrupted_data")
    
    # Nadpisz plik danych nieprawidłową zawartością
    with open(data_path, "w") as f:
        f.write("invalid json or pickle data")
        
    # get() powinno zwrócić None lub wartość domyślną
    assert cache.get("corrupted_data") is None
    assert cache.get("corrupted_data", "default") == "default"

def test_missing_data_file(disk_cache):
    """Test obsługi brakujących plików danych."""
    cache, _ = disk_cache
    # Ustaw wartość
    cache.set("missing_data", "value")
    
    # Pobierz ścieżki plików
    data_path, meta_path = cache._get_cache_file_path("missing_data")
    
    # Usuń plik danych
    os.remove(data_path)
    
    # get() powinno zwrócić None
    assert cache.get("missing_data") is None

def test_is_cache_valid(disk_cache):
    """Test sprawdzania ważności wpisu w cache'u."""
    cache, _ = disk_cache
    # Ustaw wartość
    cache.set("valid", "value", ttl=100)
    
    # Wpis powinien być ważny
    assert cache._is_cache_valid("valid")
    
    # Ustaw wartość z krótkim TTL
    cache.set("invalid", "value", ttl=1)
    time.sleep(1.1)
    
    # Wpis powinien być nieważny
    assert not cache._is_cache_valid("invalid")
    
    # Nieistniejący wpis powinien być nieważny
    assert not cache._is_cache_valid("nonexistent")

def test_large_data(disk_cache):
    """Test obsługi dużej ilości danych."""
    cache, _ = disk_cache
    # Utwórz duży słownik (około 1MB)
    large_data = {"key" + str(i): "x" * 1000 for i in range(1000)}
    
    # Zapisz dane
    cache.set("large_data", large_data)
    
    # Odczytaj dane
    retrieved = cache.get("large_data")
    
    # Sprawdź, czy dane są identyczne
    assert retrieved == large_data

def test_unicode_keys_values(disk_cache):
    """Test obsługi kluczy i wartości zawierających znaki Unicode."""
    cache, _ = disk_cache
    # Klucz i wartość ze znakami Unicode
    unicode_key = "klucz_z_polskimi_znakami_ąęśćżźół"
    unicode_value = "wartość z polskimi znakami ąęśćżźół"
    
    # Zapisz dane
    cache.set(unicode_key, unicode_value)
    
    # Odczytaj dane
    assert cache.get(unicode_key) == unicode_value
    
    # Sprawdź, czy pliki zostały utworzone
    data_path, meta_path = cache._get_cache_file_path(unicode_key)
    assert os.path.exists(data_path)
    assert os.path.exists(meta_path)

def test_non_existent_cache_dir():
    """Test tworzenia nieistniejącego katalogu cache'a."""
    # Utwórz ścieżkę do nieistniejącego katalogu
    temp_dir = tempfile.mkdtemp(prefix="test_disk_cache_nonexistent_")
    non_existent_dir = os.path.join(temp_dir, "non_existent_subdir")
    
    try:
        # Utwórz cache z nieistniejącym katalogiem
        cache = DiskCache(ttl=10, cache_dir=non_existent_dir)
        
        # Katalog powinien zostać utworzony
        assert os.path.exists(non_existent_dir)
    finally:
        # Usuń tymczasowy katalog
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def test_none_value(disk_cache):
    """Test zapisywania i odczytywania wartości None."""
    cache, _ = disk_cache
    # Zapisz None
    cache.set("none_key", None)
    
    # Odczytaj wartość
    assert cache.get("none_key") is None 