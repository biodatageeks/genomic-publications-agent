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
from pathlib import Path
import re

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
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value from the cache.
        
        Args:
            key: Cache key
            default: Default value to return if key not found
            
        Returns:
            Cached value or default if not found or expired
        """
        raise NotImplementedError("Subclasses must implement get()")
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Stores a value in the cache.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live for this specific entry (overrides default)
            
        Returns:
            True if the value was successfully stored
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
    
    def __init__(self, ttl: int = 86400, max_size: Optional[int] = None):
        """
        Initializes the memory cache.
        
        Args:
            ttl: Time-to-live for cache entries in seconds (default: 24h)
            max_size: Maximum number of entries to store (default: unlimited)
        """
        super().__init__(ttl)
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.cache_expiry: Dict[str, float] = {}
        self.max_size = max_size
        self._access_order: list = []  # For LRU eviction
        self.logger.info(f"Initialized memory cache with TTL of {ttl}s and max_size of {max_size}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value from the cache.
        
        Args:
            key: Cache key
            default: Default value to return if key not found
            
        Returns:
            Cached value or default if not found or expired
        """
        if key not in self.cache:
            return default
        
        # Check if entry has expired
        if key in self.cache_expiry and time.time() > self.cache_expiry[key]:
            self.logger.debug(f"Cache entry expired for key: {key}")
            self.delete(key)
            return default
        
        # Update access timestamp
        self.cache_timestamps[key] = time.time()
        
        # Update access order (move to end - most recently used)
        hashed_key = self._hash_key(key)
        if hashed_key in self._access_order:
            self._access_order.remove(hashed_key)
        self._access_order.append(hashed_key)
        
        self.logger.debug(f"Cache hit for key: {key}")
        return self.cache[key]
    
    def has(self, key: str) -> bool:
        """
        Checks if a key exists in the cache and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and is not expired, False otherwise
        """
        if key not in self.cache:
            return False
        
        # Check if entry has expired
        if key in self.cache_expiry and time.time() > self.cache_expiry[key]:
            self.logger.debug(f"Cache entry expired for key: {key}")
            self.delete(key)
            return False
        
        return True
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Stores a value in the cache.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live for this specific entry (overrides default)
            
        Returns:
            True if the value was successfully stored
        """
        # Use provided TTL or default
        effective_ttl = ttl if ttl is not None else self.ttl
        
        hashed_key = self._hash_key(key)
        
        # If key already exists, remove it from access order
        if key in self.cache:
            if hashed_key in self._access_order:
                self._access_order.remove(hashed_key)
        
        # Check if we need to evict entries due to max_size
        if self.max_size is not None and len(self.cache) >= self.max_size and key not in self.cache:
            # Remove least recently used entry
            if self._access_order:
                lru_hashed_key = self._access_order.pop(0)
                # Find the actual key from hashed key (for now we'll just remove the oldest)
                keys_to_remove = []
                for k in self.cache.keys():
                    if self._hash_key(k) == lru_hashed_key:
                        keys_to_remove.append(k)
                        break
                for k in keys_to_remove:
                    self._remove_from_memory(k)
                    self.logger.debug(f"Evicted LRU entry: {k}")
        
        # Store value and metadata
        self.cache[key] = value
        self.cache_timestamps[key] = time.time()
        if effective_ttl == 0:
            # TTL=0 means expire immediately
            self.cache_expiry[key] = time.time()
        elif effective_ttl > 0:
            self.cache_expiry[key] = time.time() + effective_ttl
        
        # Add to end of access order (most recently used)
        self._access_order.append(hashed_key)
        
        self.logger.debug(f"Cached value for key: {key}")
        return True
    
    def delete(self, key: str) -> None:
        """
        Deletes a value from the cache.
        
        Args:
            key: Cache key
        """
        self._remove_from_memory(key)
    
    def clear(self) -> None:
        """
        Clears all entries from the cache.
        """
        self.cache.clear()
        self.cache_timestamps.clear()
        self.cache_expiry.clear()
        self._access_order.clear()
        self.logger.info("Cleared all entries from memory cache")
    
    def _remove_from_memory(self, key: str) -> None:
        """
        Removes a key from all cache structures.
        
        Args:
            key: Cache key to remove
        """
        if key in self.cache:
            del self.cache[key]
        if key in self.cache_timestamps:
            del self.cache_timestamps[key]
        if key in self.cache_expiry:
            del self.cache_expiry[key]
        
        # Remove from access order
        hashed_key = self._hash_key(key)
        if hashed_key in self._access_order:
            self._access_order.remove(hashed_key)
        
        self.logger.debug(f"Deleted cache entry for key: {key}")
    
    def _clean_memory_cache(self) -> None:
        """
        Removes expired entries from the cache.
        """
        current_time = time.time()
        keys_to_remove = []
        
        for key, expiry_time in self.cache_expiry.items():
            if current_time > expiry_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self._remove_from_memory(key)
        
        if keys_to_remove:
            self.logger.info(f"Cleaned {len(keys_to_remove)} expired entries from memory cache")
    
    def invalidate_by_prefix(self, prefix: str) -> int:
        """
        Invalidates all cache entries with keys starting with the given prefix.
        
        Args:
            prefix: Key prefix to match
            
        Returns:
            Number of entries removed
        """
        keys_to_delete = []
        for key in list(self.cache.keys()):
            if key.startswith(prefix):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            self._remove_from_memory(key)
        
        self.logger.info(f"Invalidated {len(keys_to_delete)} cache entries with prefix: {prefix}")
        return len(keys_to_delete)
    
    def cached(self, key: str = None):
        """
        Decorator for caching function results.
        
        Args:
            key: Cache key to use (if None, will use function name with arguments)
        """
        cache = self
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Generate key if not provided
                cache_key = key
                if cache_key is None:
                    cache_key = f"{func.__name__}:{repr(args)}:{repr(kwargs)}"
                
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                cache.set(cache_key, result)
                return result
            return wrapper
        return decorator


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
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value from the cache.
        
        Args:
            key: Cache key
            default: Default value to return if key not found
            
        Returns:
            Cached value or default if not found or expired
        """
        data_path, meta_path = self._get_cache_file_path(key)
        file_path = str(data_path)
        meta_file_path = str(meta_path)
        pickle_path = file_path.replace('.cache', '.pickle')
        
        # Check metadata first
        if not os.path.exists(meta_file_path):
            return default
            
        try:
            with open(meta_file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading metadata file for key {key}: {str(e)}")
            self.delete(key)
            return default
            
        # Check if entry has expired
        if time.time() > metadata['expires_at']:
            self.logger.debug(f"Cache entry expired for key: {key}")
            self.delete(key)
            return default
            
        entry = None
        
        # Try JSON first
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading JSON cache file for key {key}: {str(e)}")
                self.delete(key)
                return default
        # Try pickle
        elif os.path.exists(pickle_path):
            try:
                import pickle
                with open(pickle_path, 'rb') as f:
                    entry = pickle.load(f)
            except Exception as e:
                self.logger.error(f"Error reading pickle cache file for key {key}: {str(e)}")
                self.delete(key)
                return default
        else:
            return default
        
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
        data_path, meta_path = self._get_cache_file_path(key)
        file_path = str(data_path)
        meta_file_path = str(meta_path)
        pickle_path = file_path.replace('.cache', '.pickle')
        
        # Check metadata first
        if not os.path.exists(meta_file_path):
            return False
            
        try:
            with open(meta_file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading metadata file for key {key}: {str(e)}")
            self.delete(key)
            return False
            
        # Check if entry has expired
        if time.time() > metadata['expires_at']:
            self.logger.debug(f"Cache entry expired for key: {key}")
            self.delete(key)
            return False
            
        # Check if data file exists
        if not (os.path.exists(file_path) or os.path.exists(pickle_path)):
            return False
            
        return True
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Stores a value in the cache.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live for this specific entry (overrides default)
            
        Returns:
            True if the value was successfully stored
        """
        data_path, meta_path = self._get_cache_file_path(key)
        file_path = str(data_path)
        meta_file_path = str(meta_path)
        
        # Use provided TTL or default
        effective_ttl = ttl if ttl is not None else self.ttl
        
        try:
            # Create metadata entry
            metadata = {
                'created_at': time.time(),
                'expires_at': time.time() + effective_ttl,
                'key': key,  # Store original key for reference
                'ttl': effective_ttl
            }
            
            # Create data entry
            entry = {
                'value': value,
                'created_at': time.time()
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save metadata
            with open(meta_file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f)
            
            # Try JSON first, fallback to pickle
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(entry, f)
                self.logger.debug(f"Cached value for key: {key} (JSON)")
            except (TypeError, ValueError) as json_error:
                # Remove the failed JSON file if it was created
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Fallback to pickle for non-JSON serializable objects
                import pickle
                pickle_path = file_path.replace('.cache', '.pickle')
                with open(pickle_path, 'wb') as f:
                    pickle.dump(entry, f)
                self.logger.debug(f"Cached value for key: {key} (pickle)")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error writing cache file for key {key}: {str(e)}")
            # Clean up any partially written files
            self.delete(key)
            raise CacheError(f"Failed to write to disk cache: {str(e)}") from e
    
    def delete(self, key: str) -> None:
        """
        Deletes a value from the cache.
        
        Args:
            key: Cache key
        """
        data_path, meta_path = self._get_cache_file_path(key)
        file_path = str(data_path)
        meta_file_path = str(meta_path)
        pickle_path = file_path.replace('.cache', '.pickle')
        
        # Delete metadata file
        if os.path.exists(meta_file_path):
            try:
                os.remove(meta_file_path)
                self.logger.debug(f"Deleted metadata file for key: {key}")
            except Exception as e:
                self.logger.error(f"Error deleting metadata file for key {key}: {str(e)}")
        
        # Delete JSON file if exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.logger.debug(f"Deleted JSON cache entry for key: {key}")
            except Exception as e:
                self.logger.error(f"Error deleting JSON cache file for key {key}: {str(e)}")
        
        # Delete pickle file if exists
        if os.path.exists(pickle_path):
            try:
                os.remove(pickle_path)
                self.logger.debug(f"Deleted pickle cache entry for key: {key}")
            except Exception as e:
                self.logger.error(f"Error deleting pickle cache file for key {key}: {str(e)}")
    
    def clear(self) -> None:
        """
        Clears all entries from the cache.
        """
        try:
            for root, _, files in os.walk(self.cache_dir):
                for file in files:
                    if file.endswith(('.cache', '.pickle', '.meta')):
                        try:
                            os.remove(os.path.join(root, file))
                        except Exception as e:
                            self.logger.error(f"Error deleting cache file {file}: {str(e)}")
            self.logger.info("Cleared all entries from disk cache")
        except Exception as e:
            self.logger.error(f"Error clearing disk cache: {str(e)}")
            raise CacheError(f"Failed to clear disk cache: {str(e)}") from e
    
    def _get_file_path(self, key: str) -> str:
        """
        Gets the file path for a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            File path for the cache entry
        """
        return os.path.join(self.cache_dir, self._generate_disk_key(key))
    
    def _get_cache_file_path(self, key: str) -> tuple:
        """
        Gets the file paths for a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            Tuple of (data_path, meta_path)
        """
        from pathlib import Path
        safe_key = self._generate_disk_key(key)
        # If the safe_key already ends with .cache, use it directly
        if safe_key.endswith('.cache'):
            cache_file = os.path.join(self.cache_dir, safe_key)
        else:
            cache_file = os.path.join(self.cache_dir, safe_key + '.cache')
        
        return (
            Path(cache_file),
            Path(cache_file + '.meta')
        )
    
    def _generate_disk_key(self, key: str) -> str:
        """
        Generates a safe disk key from a cache key.
        
        Args:
            key: Original cache key
            
        Returns:
            Safe disk key
        """
        import re
        # Replace unsafe characters with underscores
        safe_key = re.sub(r'[<>:"/\\|?*]', '_', key)
        
        # If key is too long, use hash
        if len(safe_key) > 100:
            return self._hash_key(key)
        
        # Return safe key with .cache extension for test compatibility
        return f"{safe_key}.cache"
    
    def _is_cache_valid(self, key: str) -> bool:
        """
        Checks if a cache entry is valid.
        
        Args:
            key: Cache key
            
        Returns:
            True if cache entry is valid, False otherwise
        """
        return self.has(key)
    
    def invalidate_by_prefix(self, prefix: str) -> int:
        """
        Invalidates all cache entries with keys starting with the given prefix.
        
        Args:
            prefix: Key prefix to match
            
        Returns:
            Number of entries invalidated
        """
        count = 0
        try:
            for root, _, files in os.walk(self.cache_dir):
                for file in files:
                    if file.endswith('.meta'):
                        try:
                            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                                if metadata.get('key', '').startswith(prefix):
                                    self.delete(metadata['key'])
                                    count += 1
                        except Exception as e:
                            self.logger.error(f"Error reading metadata file {file}: {str(e)}")
            self.logger.info(f"Invalidated {count} cache entries with prefix: {prefix}")
            return count
        except Exception as e:
            self.logger.error(f"Error invalidating cache entries: {str(e)}")
            raise CacheError(f"Failed to invalidate cache entries: {str(e)}") from e


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