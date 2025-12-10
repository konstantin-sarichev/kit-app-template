"""Caching system for documentation content."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

import aiofiles

from .config import CACHE_DIR, CACHE_HOURS, ensure_cache_dir


class DocCache:
    """Simple file-based cache for documentation content."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache."""
        self.cache_dir = cache_dir or ensure_cache_dir()
        self.cache_duration = CACHE_HOURS * 3600  # Convert to seconds

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        # Create hash of key to use as filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value if it exists and is not expired."""
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            # Check if expired
            if time.time() - data["timestamp"] > self.cache_duration:
                cache_path.unlink()  # Delete expired cache
                return None

            return data["value"]
        except (json.JSONDecodeError, KeyError, OSError):
            # If cache is corrupted, delete it
            if cache_path.exists():
                cache_path.unlink()
            return None

    async def set(self, key: str, value: Any) -> None:
        """Set cached value."""
        cache_path = self._get_cache_path(key)

        data = {"timestamp": time.time(), "value": value, "key": key}

        try:
            async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, indent=2))
        except OSError as e:
            # Fail silently if we can't write cache
            if __debug__:
                print(f"Warning: Could not write cache: {e}")

    async def clear(self) -> int:
        """Clear all cached items. Returns number of items deleted."""
        count = 0
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                    count += 1
                except OSError:
                    pass
        return count

    async def clear_expired(self) -> int:
        """Clear only expired cache items. Returns number of items deleted."""
        count = 0
        if self.cache_dir.exists():
            current_time = time.time()
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    async with aiofiles.open(cache_file, "r", encoding="utf-8") as f:
                        content = await f.read()
                        data = json.loads(content)

                    if current_time - data["timestamp"] > self.cache_duration:
                        cache_file.unlink()
                        count += 1
                except (json.JSONDecodeError, KeyError, OSError):
                    # Delete corrupted cache files
                    try:
                        cache_file.unlink()
                        count += 1
                    except OSError:
                        pass
        return count


# Global cache instance
_cache = DocCache()


async def get_cached(key: str) -> Optional[Any]:
    """Get cached value."""
    return await _cache.get(key)


async def set_cached(key: str, value: Any) -> None:
    """Set cached value."""
    await _cache.set(key, value)


async def clear_cache() -> int:
    """Clear all cache."""
    return await _cache.clear()


async def clear_expired_cache() -> int:
    """Clear expired cache."""
    return await _cache.clear_expired()

