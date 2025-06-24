"""
Cache management module for storing API and computation results.

This module provides functionality for caching results from API calls
and expensive computations to improve performance and reduce API usage.
"""

import os
import json
import time
import logging
from typing import Any, Optional, Dict, Union
import hashlib
from datetime import datetime

from src.models.data.clients.exceptions import CacheError


class BaseCache:
    """
    Base abstract class for all cache implementations.
    
    This class defines the interface that all cache implementations must follow.
    """
    
    def __init__(self, ttl: int = 86400):
        """
        Initializes the cache.
        
        Args:
            ttl: Time-to-live for cache entries in seconds (default: 24h)
        """
        self.ttl = ttl
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get(self, key: str) -> Any:
        """
        Retrieves a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        raise NotImplementedError("Subclasses must implement get()")
    
    def set(self, key: str, value: Any) -> None:
        """
        Stores a value in the cache.
        
        Args:
            key: Cache key
            value: Value to store
        """
        raise NotImplementedError("Subclasses must implement set()")
    
    def delete(self, key: str) -> None:
        """
        Deletes a value from the cache.
        
        Args:
            key: Cache key
        """
        raise NotImplementedError("Subclasses must implement delete()")
    
    def clear(self) -> None:
        """
        Clears all entries from the cache.
        """
        raise NotImplementedError("Subclasses must implement clear()")
    
    def _hash_key(self, key: str) -> str:
        """
        Creates a hash of the key for storage.
        
        Args:
            key: Original cache key
            
        Returns:
            Hashed key
        """
        return hashlib.md5(key.encode('utf-8')).hexdigest()


# Alias for backward compatibility
APICache = BaseCache


class MemoryCache(BaseCache):
    """
    In-memory implementation of the cache.
    
    This cache stores values in memory and is not persistent between program runs.
    It's fast but will be cleared when the program exits.
    """
    
    def __init__(self, ttl: int = 86400):
        """
        Initializes the memory cache.
        
        Args:
            ttl: Time-to-live for cache entries in seconds (default: 24h)
        """
        super().__init__(ttl)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.logger.info(f"Initialized memory cache with TTL of {ttl}s")
    
    def get(self, key: str) -> Any:
        """
        Retrieves a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        hashed_key = self._hash_key(key)
        
        if hashed_key not in self._cache:
            return None
        
        entry = self._cache[hashed_key]
        
        # Check if entry has expired
        if time.time() > entry['expires_at']:
            self.logger.debug(f"Cache entry expired for key: {key}")
            self.delete(key)
            return None
        
        self.logger.debug(f"Cache hit for key: {key}")
        return entry['value']
    
    def has(self, key: str) -> bool:
        """
        Checks if a key exists in the cache and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and is not expired, False otherwise
        """
        hashed_key = self._hash_key(key)
        
        if hashed_key not in self._cache:
            return False
        
        entry = self._cache[hashed_key]
        
        # Check if entry has expired
        if time.time() > entry['expires_at']:
            self.logger.debug(f"Cache entry expired for key: {key}")
            self.delete(key)
            return False
        
        return True
    
    def set(self, key: str, value: Any) -> None:
        """
        Stores a value in the cache.
        
        Args:
            key: Cache key
            value: Value to store
        """
        hashed_key = self._hash_key(key)
        
        # Create cache entry with expiration
        self._cache[hashed_key] = {
            'value': value,
            'created_at': time.time(),
            'expires_at': time.time() + self.ttl
        }
        
        self.logger.debug(f"Cached value for key: {key}")
    
    def delete(self, key: str) -> None:
        """
        Deletes a value from the cache.
        
        Args:
            key: Cache key
        """
        hashed_key = self._hash_key(key)
        
        if hashed_key in self._cache:
            del self._cache[hashed_key]
            self.logger.debug(f"Deleted cache entry for key: {key}")
    
    def clear(self) -> None:
        """
        Clears all entries from the cache.
        """
        self._cache.clear()
        self.logger.info("Cleared all entries from memory cache")


class DiskCache(BaseCache):
    """
    Disk-based implementation of the cache.
    
    This cache stores values on disk and is persistent between program runs.
    It's slower than memory cache but can handle larger data and survives restarts.
    """
    
    def __init__(self, ttl: int = 86400, cache_dir: str = None):
        """
        Initializes the disk cache.
        
        Args:
            ttl: Time-to-live for cache entries in seconds (default: 24h)
            cache_dir: Directory to store cache files (default: data/cache)
        """
        super().__init__(ttl)
        
        # Set default cache directory if not provided
        if cache_dir is None:
            cache_dir = os.path.join("data", "cache")
        
        self.cache_dir = cache_dir
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.logger.info(f"Initialized disk cache in {self.cache_dir} with TTL of {ttl}s")
    
    def get(self, key: str) -> Any:
        """
        Retrieves a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        file_path = self._get_file_path(key)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
            
            # Check if entry has expired
            if time.time() > entry['expires_at']:
                self.logger.debug(f"Cache entry expired for key: {key}")
                self.delete(key)
                return None
            
            self.logger.debug(f"Cache hit for key: {key}")
            return entry['value']
            
        except Exception as e:
            self.logger.error(f"Error reading cache file for key {key}: {str(e)}")
            # Delete corrupted cache file
            self.delete(key)
            return None
    
    def has(self, key: str) -> bool:
        """
        Checks if a key exists in the cache and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and is not expired, False otherwise
        """
        file_path = self._get_file_path(key)
        
        if not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
            
            # Check if entry has expired
            if time.time() > entry['expires_at']:
                self.logger.debug(f"Cache entry expired for key: {key}")
                self.delete(key)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error reading cache file for key {key}: {str(e)}")
            # Delete corrupted cache file
            self.delete(key)
            return False
    
    def set(self, key: str, value: Any) -> None:
        """
        Stores a value in the cache.
        
        Args:
            key: Cache key
            value: Value to store
        """
        file_path = self._get_file_path(key)
        
        try:
            # Create cache entry with expiration
            entry = {
                'value': value,
                'created_at': time.time(),
                'expires_at': time.time() + self.ttl,
                'key': key  # Store original key for reference
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(entry, f)
            
            self.logger.debug(f"Cached value for key: {key}")
            
        except Exception as e:
            self.logger.error(f"Error writing cache file for key {key}: {str(e)}")
            raise CacheError(f"Failed to write to disk cache: {str(e)}") from e
    
    def delete(self, key: str) -> None:
        """
        Deletes a value from the cache.
        
        Args:
            key: Cache key
        """
        file_path = self._get_file_path(key)
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.logger.debug(f"Deleted cache entry for key: {key}")
            except Exception as e:
                self.logger.error(f"Error deleting cache file for key {key}: {str(e)}")
    
    def clear(self) -> None:
        """
        Clears all entries from the cache.
        """
        try:
            # Only remove files, not directories
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            
            self.logger.info(f"Cleared all entries from disk cache in {self.cache_dir}")
            
        except Exception as e:
            self.logger.error(f"Error clearing disk cache: {str(e)}")
            raise CacheError(f"Failed to clear disk cache: {str(e)}") from e
    
    def _get_file_path(self, key: str) -> str:
        """
        Converts a cache key to a file path.
        
        Args:
            key: Cache key
            
        Returns:
            Path to the cache file
        """
        hashed_key = self._hash_key(key)
        return os.path.join(self.cache_dir, f"{hashed_key}.json")


class CacheManager:
    """
    Factory class for creating cache instances.
    
    This class provides methods to create and manage different types of caches.
    """
    
    @staticmethod
    def create(storage_type: str = "memory", ttl: int = 86400, 
               cache_dir: str = None) -> Union[MemoryCache, DiskCache]:
        """
        Creates a cache instance based on the specified type.
        
        Args:
            storage_type: Type of cache to create ("memory" or "disk")
            ttl: Time-to-live for cache entries in seconds
            cache_dir: Directory for disk cache (only used for disk cache)
            
        Returns:
            Cache instance
            
        Raises:
            ValueError: If an invalid storage type is specified
        """
        logger = logging.getLogger("CacheManager")
        
        if storage_type.lower() == "memory":
            logger.info(f"Creating memory cache with TTL of {ttl}s")
            return MemoryCache(ttl=ttl)
        elif storage_type.lower() == "disk":
            logger.info(f"Creating disk cache with TTL of {ttl}s")
            return DiskCache(ttl=ttl, cache_dir=cache_dir)
        else:
            raise ValueError(f"Invalid cache storage type: {storage_type}. Must be 'memory' or 'disk'.") 