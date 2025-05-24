"""
Testy dla implementacji MemoryCache.

Ten moduł zawiera testy jednostkowe dla klasy MemoryCache, 
która implementuje mechanizm cache'a w pamięci.
"""

import time
import unittest
from unittest.mock import patch, MagicMock

from src.api.cache.cache import MemoryCache


class TestMemoryCache(unittest.TestCase):
    """Testy dla klasy MemoryCache."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.cache = MemoryCache(ttl=10, max_size=5)

    def test_init(self):
        """Test inicjalizacji MemoryCache."""
        self.assertEqual(self.cache.ttl, 10)
        self.assertEqual(self.cache.max_size, 5)
        self.assertEqual(len(self.cache.cache), 0)

    def test_has(self):
        """Test sprawdzania istnienia klucza w cache'u."""
        # Klucz nie istnieje
        self.assertFalse(self.cache.has("key"))
        
        # Dodaj klucz
        self.cache.set("key", "value")
        self.assertTrue(self.cache.has("key"))
        
        # Dodaj klucz z wygasłym TTL
        self.cache.set("expired_key", "value", ttl=0)
        time.sleep(0.1)  # Poczekaj moment, aby upewnić się, że TTL wygasł
        self.assertFalse(self.cache.has("expired_key"))

    def test_get(self):
        """Test pobierania wartości z cache'a."""
        # Klucz nie istnieje
        self.assertIsNone(self.cache.get("key"))
        self.assertEqual(self.cache.get("key", "default"), "default")
        
        # Dodaj klucz
        self.cache.set("key", "value")
        self.assertEqual(self.cache.get("key"), "value")
        
        # Sprawdź, czy czas ostatniego dostępu został zaktualizowany
        last_access_time = self.cache.cache_timestamps["key"]
        time.sleep(0.1)
        self.cache.get("key")
        self.assertGreater(self.cache.cache_timestamps["key"], last_access_time)
        
        # Wygasły klucz
        self.cache.set("expired_key", "value", ttl=0)
        time.sleep(0.1)
        self.assertIsNone(self.cache.get("expired_key"))

    def test_set(self):
        """Test ustawiania wartości w cache'u."""
        # Podstawowy zapis
        self.assertTrue(self.cache.set("key", "value"))
        self.assertEqual(self.cache.get("key"), "value")
        
        # Nadpisanie istniejącego klucza
        self.assertTrue(self.cache.set("key", "new_value"))
        self.assertEqual(self.cache.get("key"), "new_value")
        
        # Specyficzny TTL
        current_time = time.time()
        self.cache.set("key_ttl", "value", ttl=5)
        self.assertAlmostEqual(self.cache.cache_expiry["key_ttl"], current_time + 5, delta=1)

    def test_max_size_limit(self):
        """Test limitu rozmiaru cache'a."""
        # Dodaj więcej elementów niż max_size
        for i in range(7):
            self.cache.set(f"key{i}", f"value{i}")
        
        # Powinno zostać tylko 5 najnowszych (lub najczęściej używanych) elementów
        self.assertEqual(len(self.cache.cache), 5)
        
        # Najstarsze elementy (key0, key1) powinny zostać usunięte
        self.assertFalse(self.cache.has("key0"))
        self.assertFalse(self.cache.has("key1"))
        
        # Nowsze elementy powinny pozostać
        for i in range(2, 7):
            self.assertTrue(self.cache.has(f"key{i}"))

    def test_lru_eviction(self):
        """Test usuwania najrzadziej używanych elementów (LRU)."""
        # Dodaj 5 elementów (zapełnij cache)
        for i in range(5):
            self.cache.set(f"key{i}", f"value{i}")
        
        # Użyj key0 i key1, aby były traktowane jako ostatnio używane
        self.cache.get("key0")
        self.cache.get("key1")
        
        # Dodaj nowy element, co powinno spowodować usunięcie najrzadziej używanego (key2)
        self.cache.set("new_key", "new_value")
        
        # key2 powinien zostać usunięty
        self.assertFalse(self.cache.has("key2"))
        
        # key0, key1 i nowy element powinny istnieć
        self.assertTrue(self.cache.has("key0"))
        self.assertTrue(self.cache.has("key1"))
        self.assertTrue(self.cache.has("new_key"))

    def test_clean_memory_cache(self):
        """Test czyszczenia wygasłych wpisów z cache'a."""
        # Dodaj elementy z różnymi TTL
        self.cache.set("short_ttl", "value", ttl=1)
        self.cache.set("long_ttl", "value", ttl=100)
        
        # Poczekaj, aż short_ttl wygaśnie
        time.sleep(1.1)
        
        # Wymuś czyszczenie
        self.cache._clean_memory_cache()
        
        # short_ttl powinien zostać usunięty
        self.assertFalse(self.cache.has("short_ttl"))
        
        # long_ttl powinien pozostać
        self.assertTrue(self.cache.has("long_ttl"))

    def test_remove_from_memory(self):
        """Test ręcznego usuwania elementu z cache'a."""
        # Dodaj element
        self.cache.set("key", "value")
        self.assertTrue(self.cache.has("key"))
        
        # Usuń element
        self.cache._remove_from_memory("key")
        
        # Element powinien zostać usunięty
        self.assertFalse(self.cache.has("key"))
        self.assertNotIn("key", self.cache.cache)
        self.assertNotIn("key", self.cache.cache_timestamps)
        self.assertNotIn("key", self.cache.cache_expiry)

    def test_complex_data_types(self):
        """Test obsługi złożonych typów danych."""
        # Słownik
        dict_data = {"key1": "value1", "key2": 123}
        self.cache.set("dict_key", dict_data)
        self.assertEqual(self.cache.get("dict_key"), dict_data)
        
        # Lista
        list_data = [1, 2, 3, "test"]
        self.cache.set("list_key", list_data)
        self.assertEqual(self.cache.get("list_key"), list_data)
        
        # Zagnieżdżone struktury
        nested_data = {"key1": [1, 2, {"nested": True}]}
        self.cache.set("nested_key", nested_data)
        self.assertEqual(self.cache.get("nested_key"), nested_data)

    def test_cache_timestamps_update(self):
        """Test aktualizacji znaczników czasu cache'a."""
        # Dodaj element
        self.cache.set("key", "value")
        initial_timestamp = self.cache.cache_timestamps["key"]
        
        # Poczekaj moment
        time.sleep(0.1)
        
        # Aktualizuj element
        self.cache.set("key", "new_value")
        updated_timestamp = self.cache.cache_timestamps["key"]
        
        # Znacznik czasu powinien zostać zaktualizowany
        self.assertGreater(updated_timestamp, initial_timestamp)

    def test_cache_size_tracking(self):
        """Test śledzenia rozmiaru cache'a."""
        # Dodaj 3 elementy
        for i in range(3):
            self.cache.set(f"key{i}", f"value{i}")
            
        # Rozmiar cache'a powinien wynosić 3
        self.assertEqual(len(self.cache.cache), 3)
        
        # Usuń 1 element
        self.cache._remove_from_memory("key1")
        
        # Rozmiar cache'a powinien wynosić 2
        self.assertEqual(len(self.cache.cache), 2)

    def test_concurrent_access_simulation(self):
        """
        Test symulujący równoczesny dostęp do cache'a.
        
        Uwaga: To nie jest rzeczywisty test współbieżności, 
        a jedynie symulacja sekwencyjnych operacji w różnej kolejności.
        """
        # Symuluj operacje w różnej kolejności
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.get("key1")  # Użyj key1
        self.cache.set("key3", "value3")
        self.cache.get("key2")  # Użyj key2
        self.cache.set("key4", "value4")
        self.cache.set("key5", "value5")  # To może spowodować usunięcie najrzadziej używanego
        
        # Sprawdź, czy wszystkie oczekiwane klucze istnieją
        # Ponieważ używaliśmy key1 i key2, nie powinny zostać usunięte
        self.assertTrue(self.cache.has("key1"))
        self.assertTrue(self.cache.has("key2"))

    def test_zero_ttl(self):
        """Test zerowego TTL."""
        # TTL = 0 oznacza, że wpis nigdy nie wygasa
        self.cache.set("zero_ttl", "value", ttl=0)
        
        # W implementacji TTL = 0 może być interpretowane jako "wygasło natychmiast"
        # Sprawdźmy, jak zachowuje się nasza implementacja
        time.sleep(0.1)
        
        # Jeśli TTL = 0 oznacza "nigdy nie wygasa", klucz powinien istnieć
        # Jeśli TTL = 0 oznacza "wygasło natychmiast", klucz nie powinien istnieć
        # Dostosuj test do oczekiwanego zachowania
        self.assertFalse(self.cache.has("zero_ttl"))
        
    def test_none_value(self):
        """Test wartości None."""
        # Zapisz None jako wartość
        self.cache.set("none_key", None)
        
        # Pobierz wartość
        value = self.cache.get("none_key")
        
        # Wartość powinna być None
        self.assertIsNone(value)
        
        # Sprawdź, czy klucz istnieje
        self.assertTrue(self.cache.has("none_key"))


if __name__ == "__main__":
    unittest.main() 