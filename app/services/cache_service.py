"""
Caching service for parsed data with TTL support
"""

import time
import logging
from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    data: Any
    created_at: float
    file_mtime: Optional[float] = None
    ttl: float = 5.0  # Default 5 second TTL


class CacheService:
    """
    Thread-safe caching service with TTL and file modification tracking.

    Features:
    - Time-based expiration (TTL)
    - File modification time tracking (auto-invalidate when file changes)
    - Thread-safe operations
    - Memory-bounded (max entries)
    """

    def __init__(self, default_ttl: float = 5.0, max_entries: int = 100):
        """
        Initialize cache service.

        Args:
            default_ttl: Default time-to-live in seconds
            max_entries: Maximum number of cache entries
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._hits = 0
        self._misses = 0

    def get(
        self,
        key: str,
        file_path: Optional[Path] = None
    ) -> Optional[Any]:
        """
        Get value from cache if valid.

        Args:
            key: Cache key
            file_path: If provided, invalidate if file has been modified

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            # Check TTL
            if time.time() - entry.created_at > entry.ttl:
                del self._cache[key]
                self._misses += 1
                return None

            # Check file modification time
            if file_path and entry.file_mtime:
                try:
                    current_mtime = file_path.stat().st_mtime
                    if current_mtime > entry.file_mtime:
                        del self._cache[key]
                        self._misses += 1
                        return None
                except OSError:
                    # File doesn't exist, invalidate cache
                    del self._cache[key]
                    self._misses += 1
                    return None

            self._hits += 1
            return entry.data

    def set(
        self,
        key: str,
        data: Any,
        ttl: Optional[float] = None,
        file_path: Optional[Path] = None
    ) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key
            data: Data to cache
            ttl: Time-to-live in seconds (uses default if not provided)
            file_path: If provided, track file modification time
        """
        with self._lock:
            # Enforce max entries
            if len(self._cache) >= self._max_entries and key not in self._cache:
                self._evict_oldest()

            file_mtime = None
            if file_path:
                try:
                    file_mtime = file_path.stat().st_mtime
                except OSError:
                    pass

            self._cache[key] = CacheEntry(
                data=data,
                created_at=time.time(),
                file_mtime=file_mtime,
                ttl=ttl or self._default_ttl
            )

    def invalidate(self, key: str) -> bool:
        """
        Remove entry from cache.

        Args:
            key: Cache key

        Returns:
            True if entry was removed, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """
        Remove all entries with keys starting with prefix.

        Args:
            prefix: Key prefix

        Returns:
            Number of entries removed
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: Optional[float] = None,
        file_path: Optional[Path] = None
    ) -> Any:
        """
        Get value from cache or compute and store it.

        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            ttl: Time-to-live in seconds
            file_path: If provided, track file modification time

        Returns:
            Cached or computed value
        """
        # Try cache first
        cached = self.get(key, file_path=file_path)
        if cached is not None:
            return cached

        # Compute and cache
        data = compute_fn()
        self.set(key, data, ttl=ttl, file_path=file_path)
        return data

    def _evict_oldest(self) -> None:
        """Evict oldest cache entry (must be called with lock held)"""
        if not self._cache:
            return

        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )
        del self._cache[oldest_key]

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                'entries': len(self._cache),
                'max_entries': self._max_entries,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': f"{hit_rate:.1f}%"
            }


# Global cache instance
_cache = CacheService()


def get_cache() -> CacheService:
    """Get the global cache service instance"""
    return _cache
