# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for cache module."""

import tempfile
from dataclasses import dataclass

import pytest

from mcp_nix.cache import APIError, Cache


@dataclass
class IncompatibleCachedValue:
    """An incompatible cached value that doesn't have expected attributes."""

    some_field: str


def test_cache_fails_with_incompatible_value_on_direct_access():
    """Test that direct cache access fails with incompatible value.

    This demonstrates why we need recovery logic - if we just use
    cache.get() directly, incompatible values will cause errors.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = Cache(tmpdir)
        key = "test_key"

        # Store an incompatible value directly
        incompatible = IncompatibleCachedValue(some_field="old format")
        cache.set(key, incompatible)

        # Direct access returns the incompatible value
        cached = cache.get(key)
        assert cached is not None

        # Accessing expected attributes fails
        with pytest.raises(AttributeError, match="content_type"):
            _ = cached.content_type


def test_get_or_set_retries_on_callback_failure():
    """Test that get_or_set retries with fresh value when callback fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = Cache(tmpdir)
        key = "test_key"

        # Store an incompatible value
        cache.set(key, {"old": "format"})

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"new": "format", "data": 42}

        # Callback that fails on old format but works on new
        def callback(value):
            return value["data"]  # Will fail on old format (no "data" key)

        result = cache.get_or_set(key, factory, callback=callback)

        # Factory should have been called (retry after callback failure)
        assert call_count == 1
        assert result == 42

        # Cache should now have the new format
        assert cache.get(key) == {"new": "format", "data": 42}


def test_get_or_set_uses_cached_value_when_callback_succeeds():
    """Test that get_or_set uses cached value when callback succeeds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = Cache(tmpdir)
        key = "test_key"

        # Store a compatible value
        cache.set(key, {"data": 100})

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"data": 999}

        result = cache.get_or_set(key, factory, callback=lambda v: v["data"])

        # Factory should NOT have been called
        assert call_count == 0
        assert result == 100


def test_get_or_set_calls_factory_on_cache_miss():
    """Test that get_or_set calls factory when cache is empty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = Cache(tmpdir)
        key = "test_key"

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"data": 42}

        result = cache.get_or_set(key, factory, callback=lambda v: v["data"])

        assert call_count == 1
        assert result == 42
        assert cache.get(key) == {"data": 42}


def test_request_recovers_from_incompatible_cached_value():
    """Test that request() recovers when callback fails on cached value."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = Cache(tmpdir)
        url = "https://httpbin.org/get"

        # Store an incompatible value directly
        incompatible = IncompatibleCachedValue(some_field="old format")
        cache.set(url, incompatible)

        # Request with callback that accesses .json() - will fail on incompatible
        # value, triggering refetch from actual URL
        result = cache.request(url, callback=lambda r: r.json())

        # Should have fetched fresh data
        assert isinstance(result, dict)
        assert "url" in result

        # Cache should now have valid data
        from mcp_nix.cache import CachedResponse

        assert isinstance(cache.get(url), CachedResponse)


def test_request_handles_404():
    """Test that request() raises APIError for 404 responses."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = Cache(tmpdir)
        url = "https://httpbin.org/status/404"

        with pytest.raises(APIError, match="404"):
            cache.request(url, lambda r: r.json())

        # Verify nothing was cached
        assert cache.get(url) is None
