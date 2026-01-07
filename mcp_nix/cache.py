"""Shared caching utilities using diskcache."""

from collections.abc import Callable

from diskcache import Cache
from platformdirs import user_cache_dir

DEFAULT_EXPIRE = 60 * 60  # 1 hour


def get_cache(name: str) -> Cache:
    """Get a cache instance for the given namespace."""
    return Cache(f"{user_cache_dir('mcp-nix')}/{name}")


def get_or_set[T](cache: Cache, key: str, factory: Callable[[], T], expire: float | None = DEFAULT_EXPIRE) -> T:
    """Get a value from cache, or create it using factory if not present."""
    value = cache.get(key)
    if value is None:
        value = factory()
        cache.set(key, value, expire=expire)
    return value
