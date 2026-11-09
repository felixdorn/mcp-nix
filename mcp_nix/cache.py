"""Shared caching utilities using diskcache."""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import diskcache
import requests
from platformdirs import user_cache_dir
from requests.structures import CaseInsensitiveDict

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

DEFAULT_EXPIRE = 60 * 60  # 1 hour
DEFAULT_TIMEOUT = 5  # Aggressive timeout - most APIs respond quickly


class APIError(Exception):
    """Custom exception for API-related errors."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class CachedResponse:
    """Cacheable HTTP response with parsing helpers."""

    content: bytes
    status_code: int
    headers: CaseInsensitiveDict[str]
    url: str

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self.text)

    def yaml(self) -> Any:
        import yaml

        return yaml.safe_load(self.text)

    def soup(self) -> "BeautifulSoup":  # noqa: F821
        from bs4 import BeautifulSoup

        return BeautifulSoup(self.text, "html.parser")

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").lower()


class Cache(diskcache.Cache):
    """Extended diskcache.Cache with helper methods."""

    def get_or_set[T, R](
        self,
        key: str,
        factory: Callable[[], T],
        callback: Callable[[T], R],
        expire: float | None = DEFAULT_EXPIRE,
    ) -> R:
        """Get cached value or create with factory, processed through callback.

        If callback fails with cached value, invalidates cache and retries once
        with a fresh value. This allows the callback to serve as validation -
        incompatible cached values are automatically recovered.
        """
        for attempt in range(2):
            if attempt == 0:
                cached = self.get(key)
                if cached is not None:
                    try:
                        return callback(cached)
                    except Exception:
                        self.delete(key)
                        continue

            fresh = factory()
            result = callback(fresh)
            self.set(key, fresh, expire=expire)
            return result

        # Should never reach here, but satisfy type checker
        raise RuntimeError("Unreachable")  # pragma: no cover

    def request[R](
        self,
        url: str,
        callback: Callable[[CachedResponse], R],
        *,
        expire: float | None = DEFAULT_EXPIRE,
        timeout: int = DEFAULT_TIMEOUT,
        **kwargs,
    ) -> R:
        """Fetch URL with caching, processed through callback.

        If callback fails with cached value, invalidates and retries with fresh.
        The callback serves as both transformation and validation.
        """

        def factory() -> CachedResponse:
            try:
                resp = requests.get(url, timeout=timeout, **kwargs)
                resp.raise_for_status()
            except requests.Timeout as exc:
                raise APIError(f"Connection timed out: {url}") from exc
            except requests.HTTPError as exc:
                raise APIError(
                    f"Request failed ({exc.response.status_code}): {url}", status_code=exc.response.status_code
                ) from exc
            except requests.RequestException as exc:
                raise APIError(f"Connection failed: {url}") from exc

            return CachedResponse(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp.headers,
                url=str(resp.url),
            )

        # Include the effective query, headers, cookies, and auth without persisting secrets.
        key = url
        if kwargs:
            request_args = {
                k: v for k, v in kwargs.items() if k in {"params", "headers", "cookies", "auth", "data", "json"}
            }
            prepared = requests.Request("GET", url, **request_args).prepare()
            identity = repr((prepared.url, sorted(prepared.headers.items()), prepared.body))
            key = "request:" + hashlib.sha256(identity.encode()).hexdigest()

        def validate(response: CachedResponse) -> R:
            try:
                return callback(response)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise APIError(f"Invalid response from {url}: {exc}") from exc

        return self.get_or_set(key, factory, callback=validate, expire=expire)


def get_cache(name: str) -> Cache:
    """Get a cache instance for the given namespace."""
    return Cache(f"{user_cache_dir('mcp-nix')}/{name}")
