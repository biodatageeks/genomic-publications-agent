import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union


class APICache:
    """
    Uniwersalny cache do przechowywania wyników zapytań API.
    
    Umożliwia zapisywanie i odczytywanie odpowiedzi z API z określonym czasem ważności.
    Dane mogą być przechowywane w pamięci lub na dysku jako pliki JSON lub pickle.
    
    Przykład użycia:
        # Utworzenie cache'a w pamięci z 30-minutowym czasem ważności
        cache = APICache(ttl=1800)
        
        # Sprawdzenie, czy dane są w cache'u
        if cache.has("query_key"):
            data = cache.get("query_key")
        else:
            data = api.make_request()
            cache.set("query_key", data)
            
        # Alternatywnie z użyciem dekoratora:
        @cache.cached()
        def fetch_data(param1, param2):
            return api.make_request(param1, param2)
            
        # Wywołanie z automatycznym cache'owaniem
        result = fetch_data("val1", "val2")
    """
    
    def __init__(
            self,
            ttl: int = 3600,
            max_size: Optional[int] = None,
            cache_dir: Optional[str] = None,
            storage_type: str = "memory"
        ):
        """
        Inicjalizacja mechanizmu cache'a.
        
        Args:
            ttl: Czas życia wpisów w cache'u w sekundach (domyślnie 1 godzina)
            max_size: Maksymalna liczba elementów w cache'u (tylko dla cache'a w pamięci)
            cache_dir: Katalog do przechowywania plików cache (wymagany dla storage_type='disk')
            storage_type: Typ przechowywania cache'a: 'memory' (w pamięci) lub 'disk' (na dysku)
        """
        self.ttl = ttl
        self.max_size = max_size
        self.storage_type = storage_type
        self.logger = logging.getLogger(__name__)
        
        if storage_type == "disk":
            if not cache_dir:
                cache_dir = os.path.join(os.path.expanduser("~"), ".cache/clinvar_api")
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Używanie pamięci podręcznej na dysku w {self.cache_dir}")
        else:
            self.cache = {}  # W pamięci
            self.cache_timestamps = {}  # Czasy ostatniego dostępu
            self.cache_expiry = {}  # Czasy wygaśnięcia
    
    def _clean_memory_cache(self):
        """
        Czyści nieaktualne lub nadmiarowe wpisy z cache'a w pamięci.
        """
        if self.storage_type != "memory":
            return
            
        # Usuwanie wygasłych wpisów
        current_time = time.time()
        expired_keys = [k for k, exp_time in self.cache_expiry.items() if exp_time <= current_time]
        
        for key in expired_keys:
            self._remove_from_memory(key)
            
        # Jeśli nadal przekraczamy max_size, usuń najstarsze wpisy
        if self.max_size and len(self.cache) > self.max_size:
            # Sortowanie według czasu ostatniego dostępu
            sorted_keys = sorted(
                self.cache_timestamps.items(), 
                key=lambda x: x[1]
            )
            
            # Usunięcie najstarszych wpisów
            keys_to_remove = [k for k, _ in sorted_keys[:len(self.cache) - self.max_size]]
            for key in keys_to_remove:
                self._remove_from_memory(key)
    
    def _remove_from_memory(self, key: str):
        """
        Usuwa wpis z cache'a w pamięci.
        
        Args:
            key: Klucz do usunięcia
        """
        if key in self.cache:
            del self.cache[key]
        if key in self.cache_timestamps:
            del self.cache_timestamps[key]
        if key in self.cache_expiry:
            del self.cache_expiry[key]
    
    def _generate_disk_key(self, key: str) -> str:
        """
        Generuje nazwę pliku dla klucza cache'a.
        
        Args:
            key: Klucz cache'a
            
        Returns:
            Nazwa pliku dla klucza
        """
        # Zamiana niedozwolonych znaków w nazwach plików
        safe_key = "".join(c if c.isalnum() else "_" for c in str(key))
        # Ograniczenie długości nazwy pliku
        if len(safe_key) > 100:
            import hashlib
            hash_suffix = hashlib.md5(str(key).encode()).hexdigest()
            safe_key = safe_key[:50] + "_" + hash_suffix
            
        return safe_key + ".cache"
    
    def _get_cache_file_path(self, key: str) -> Tuple[Path, Path]:
        """
        Zwraca ścieżkę do pliku cache'a i pliku metadanych.
        
        Args:
            key: Klucz cache'a
            
        Returns:
            Krotka (ścieżka_do_danych, ścieżka_do_metadanych)
        """
        filename = self._generate_disk_key(key)
        data_path = self.cache_dir / filename
        meta_path = self.cache_dir / (filename + ".meta")
        return data_path, meta_path
    
    def _is_cache_valid(self, key: str) -> bool:
        """
        Sprawdza, czy wpis w cache'u jest wciąż ważny.
        
        Args:
            key: Klucz cache'a
            
        Returns:
            True jeśli wpis jest ważny, False w przeciwnym razie
        """
        current_time = time.time()
        
        if self.storage_type == "memory":
            return (
                key in self.cache and 
                key in self.cache_expiry and 
                self.cache_expiry[key] > current_time
            )
        else:  # disk
            _, meta_path = self._get_cache_file_path(key)
            if not meta_path.exists():
                return False
                
            try:
                with open(meta_path, "r") as f:
                    metadata = json.load(f)
                return metadata.get("expires_at", 0) > current_time
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Błąd odczytu metadanych cache'a dla {key}: {e}")
                return False
    
    def has(self, key: str) -> bool:
        """
        Sprawdza, czy ważny wpis istnieje w cache'u.
        
        Args:
            key: Klucz cache'a
            
        Returns:
            True jeśli ważny wpis istnieje, False w przeciwnym razie
        """
        return self._is_cache_valid(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Pobiera dane z cache'a.
        
        Args:
            key: Klucz cache'a
            default: Wartość domyślna zwracana, gdy klucz nie istnieje w cache'u
            
        Returns:
            Dane z cache'a lub wartość domyślna
        """
        if not self.has(key):
            return default
            
        if self.storage_type == "memory":
            # Aktualizacja czasu ostatniego dostępu
            self.cache_timestamps[key] = time.time()
            return self.cache[key]
        else:  # disk
            data_path, _ = self._get_cache_file_path(key)
            
            try:
                # Próba deserializacji jako JSON
                try:
                    with open(data_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Jeśli JSON się nie uda, próba deserializacji jako pickle
                    with open(data_path, "rb") as f:
                        return pickle.load(f)
            except (IOError, pickle.PickleError) as e:
                self.logger.warning(f"Błąd odczytu danych cache'a dla {key}: {e}")
                return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Zapisuje dane do cache'a.
        
        Args:
            key: Klucz cache'a
            value: Dane do zapisania
            ttl: Opcjonalny specyficzny czas życia dla tego wpisu (w sekundach)
            
        Returns:
            True jeśli zapisanie powiodło się, False w przeciwnym razie
        """
        if ttl is None:
            ttl = self.ttl
            
        current_time = time.time()
        expires_at = current_time + ttl
        
        if self.storage_type == "memory":
            self.cache[key] = value
            self.cache_timestamps[key] = current_time
            self.cache_expiry[key] = expires_at
            
            # Czyszczenie cache'a, jeśli to konieczne
            self._clean_memory_cache()
            return True
        else:  # disk
            data_path, meta_path = self._get_cache_file_path(key)
            
            try:
                # Metadane zawsze zapisujemy jako JSON
                metadata = {
                    "created_at": current_time,
                    "expires_at": expires_at,
                    "ttl": ttl
                }
                
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f)
                
                # Próba serializacji jako JSON
                try:
                    with open(data_path, "w", encoding="utf-8") as f:
                        json.dump(value, f)
                except (TypeError, OverflowError):
                    # Jeśli JSON się nie uda, użyj pickle
                    with open(data_path, "wb") as f:
                        pickle.dump(value, f)
                        
                return True
            except (IOError, pickle.PickleError) as e:
                self.logger.warning(f"Błąd zapisu danych cache'a dla {key}: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """
        Usuwa wpis z cache'a.
        
        Args:
            key: Klucz cache'a
            
        Returns:
            True jeśli usunięcie powiodło się, False w przeciwnym razie
        """
        if self.storage_type == "memory":
            if key in self.cache:
                self._remove_from_memory(key)
                return True
            return False
        else:  # disk
            data_path, meta_path = self._get_cache_file_path(key)
            
            try:
                if data_path.exists():
                    os.remove(data_path)
                if meta_path.exists():
                    os.remove(meta_path)
                return True
            except IOError as e:
                self.logger.warning(f"Błąd usuwania danych cache'a dla {key}: {e}")
                return False
    
    def clear(self) -> bool:
        """
        Czyści cały cache.
        
        Returns:
            True jeśli czyszczenie powiodło się, False w przypadku błędu
        """
        if self.storage_type == "memory":
            self.cache = {}
            self.cache_timestamps = {}
            self.cache_expiry = {}
            return True
        else:  # disk
            try:
                for file_path in self.cache_dir.glob("*.cache*"):
                    os.remove(file_path)
                return True
            except IOError as e:
                self.logger.warning(f"Błąd czyszczenia cache'a na dysku: {e}")
                return False
    
    def cached(self, key_func: Optional[Callable] = None, ttl: Optional[int] = None):
        """
        Dekorator do automatycznego cache'owania wyników funkcji.
        
        Args:
            key_func: Opcjonalna funkcja do generowania klucza cache'a na podstawie argumentów.
                     Jeśli nie podano, używa str(args) + str(kwargs)
            ttl: Opcjonalny specyficzny czas życia dla wpisów tej funkcji
            
        Returns:
            Funkcja z zaimplementowanym cache'owaniem
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Generowanie klucza cache'a
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Domyślna generacja klucza
                    cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                
                # Sprawdzenie, czy wynik jest w cache'u
                if self.has(cache_key):
                    self.logger.debug(f"Cache hit dla {cache_key}")
                    return self.get(cache_key)
                
                # Wywołanie oryginalnej funkcji
                result = func(*args, **kwargs)
                
                # Zapisanie wyniku w cache'u
                self.set(cache_key, result, ttl)
                self.logger.debug(f"Cache miss dla {cache_key}, zapisano wynik")
                
                return result
            return wrapper
        return decorator


class DiskCache(APICache):
    """
    Wygodna klasa opakowująca dla cache'a na dysku.
    """
    def __init__(
            self,
            ttl: int = 3600,
            cache_dir: Optional[str] = None
        ):
        """
        Inicjalizacja cache'a na dysku.
        
        Args:
            ttl: Czas życia wpisów w cache'u w sekundach (domyślnie 1 godzina)
            cache_dir: Katalog do przechowywania plików cache
        """
        super().__init__(ttl=ttl, cache_dir=cache_dir, storage_type="disk")


class MemoryCache(APICache):
    """
    Wygodna klasa opakowująca dla cache'a w pamięci.
    """
    def __init__(
            self,
            ttl: int = 3600,
            max_size: Optional[int] = None
        ):
        """
        Inicjalizacja cache'a w pamięci.
        
        Args:
            ttl: Czas życia wpisów w cache'u w sekundach (domyślnie 1 godzina)
            max_size: Maksymalna liczba elementów w cache'u
        """
        super().__init__(ttl=ttl, max_size=max_size, storage_type="memory") 