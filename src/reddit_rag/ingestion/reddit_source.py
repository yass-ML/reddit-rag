"""Reddit JSON source adapter.

This module uses Reddit's JSON responses for public content. It does not scrape
HTML, fake browser headers, or attempt to work around throttling.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

REDDIT_BASE_URL = "https://www.reddit.com"
DEFAULT_REQUEST_DELAY_SECONDS = 1.0
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRIES = 2


@dataclass(frozen=True)
class RateLimitInfo:
    """Rate-limit headers returned by Reddit when available."""

    used: float | None = None
    remaining: float | None = None
    reset_seconds: float | None = None


@dataclass(frozen=True)
class RedditJsonResponse:
    """A raw JSON response plus request metadata needed by ingestion."""

    url: str
    status_code: int
    headers: dict[str, str]
    payload: Any
    rate_limit: RateLimitInfo


@dataclass(frozen=True)
class JsonRedditSourceSettings:
    """Runtime settings for direct Reddit JSON access."""

    user_agent: str
    oauth_token: str | None = None
    base_url: str = REDDIT_BASE_URL
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES


class RedditSourceError(RuntimeError):
    """Raised when Reddit JSON access fails."""

    def __init__(self, message: str, *, status_code: int | None = None, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class RedditSource(Protocol):
    """Interface for fetching raw Reddit JSON payloads."""

    def fetch_subreddit_listing(
        self,
        subreddit_name: str,
        *,
        limit: int = 100,
        after: str | None = None,
        sort: str = "hot",
    ) -> RedditJsonResponse:
        """Fetch one listing page for a subreddit."""

    def fetch_thread(
        self,
        permalink: str,
        *,
        limit: int = 500,
        sort: str = "confidence",
    ) -> RedditJsonResponse:
        """Fetch a submission and comment tree from a permalink."""


class JsonRedditSource:
    """Direct HTTP client for Reddit JSON endpoints."""

    def __init__(self, settings: JsonRedditSourceSettings) -> None:
        user_agent = settings.user_agent.strip()
        if not user_agent:
            raise ValueError("REDDIT_USER_AGENT must be set for Reddit JSON access.")
        if settings.request_delay_seconds < 0:
            raise ValueError("request_delay_seconds must be >= 0.")
        if settings.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0.")
        if settings.max_retries < 0:
            raise ValueError("max_retries must be >= 0.")

        self._settings = JsonRedditSourceSettings(
            user_agent=user_agent,
            oauth_token=settings.oauth_token.strip() if settings.oauth_token else None,
            base_url=settings.base_url.rstrip("/"),
            request_delay_seconds=settings.request_delay_seconds,
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
        )
        self._last_request_at: float | None = None

    def fetch_subreddit_listing(
        self,
        subreddit_name: str,
        *,
        limit: int = 100,
        after: str | None = None,
        sort: str = "hot",
    ) -> RedditJsonResponse:
        subreddit = _clean_subreddit_name(subreddit_name)
        capped_limit = _cap_limit(limit, minimum=1, maximum=100)
        params: dict[str, str | int] = {"limit": capped_limit, "raw_json": 1}
        if after:
            params["after"] = after
        return self._fetch_json(f"/r/{subreddit}/{sort}.json", params=params)

    def fetch_thread(
        self,
        permalink: str,
        *,
        limit: int = 500,
        sort: str = "confidence",
    ) -> RedditJsonResponse:
        capped_limit = _cap_limit(limit, minimum=1, maximum=500)
        path = _permalink_to_json_path(permalink)
        params: dict[str, str | int] = {
            "limit": capped_limit,
            "raw_json": 1,
            "sort": sort,
        }
        return self._fetch_json(path, params=params)

    def _fetch_json(self, path: str, *, params: dict[str, str | int] | None = None) -> RedditJsonResponse:
        url = self._build_url(path, params=params)
        attempts = self._settings.max_retries + 1
        last_error: RedditSourceError | None = None

        for attempt in range(attempts):
            self._wait_for_request_slot()
            try:
                request = Request(url, headers=self._headers())
                with urlopen(request, timeout=self._settings.timeout_seconds) as response:
                    status_code = int(response.status)
                    headers = _headers_to_dict(response.headers)
                    body = response.read().decode("utf-8")
                return RedditJsonResponse(
                    url=url,
                    status_code=status_code,
                    headers=headers,
                    payload=json.loads(body),
                    rate_limit=_parse_rate_limit(headers),
                )
            except HTTPError as e:
                headers = _headers_to_dict(e.headers)
                retry_after = _parse_float(headers.get("retry-after"))
                message = f"Reddit JSON request failed with HTTP {e.code}: {url}"
                last_error = RedditSourceError(message, status_code=e.code, retry_after=retry_after)
                if e.code in {429, 500, 502, 503, 504} and attempt + 1 < attempts:
                    self._sleep_for_retry(retry_after, attempt)
                    continue
                raise last_error from e
            except URLError as e:
                last_error = RedditSourceError(f"Reddit JSON request failed: {e.reason}")
                if attempt + 1 < attempts:
                    self._sleep_for_retry(None, attempt)
                    continue
                raise last_error from e
            except json.JSONDecodeError as e:
                raise RedditSourceError(f"Reddit returned invalid JSON for {url}: {e}") from e

        if last_error is not None:
            raise last_error
        raise RedditSourceError(f"Reddit JSON request failed: {url}")

    def _build_url(self, path: str, *, params: dict[str, str | int] | None = None) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            base = path
        else:
            base = urljoin(f"{self._settings.base_url}/", path.lstrip("/"))

        if params:
            separator = "&" if "?" in base else "?"
            return f"{base}{separator}{urlencode(params)}"
        return base

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": self._settings.user_agent,
        }
        if self._settings.oauth_token:
            headers["Authorization"] = f"Bearer {self._settings.oauth_token}"
        return headers

    def _wait_for_request_slot(self) -> None:
        now = time.monotonic()
        if self._last_request_at is not None:
            elapsed = now - self._last_request_at
            remaining = self._settings.request_delay_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at = time.monotonic()

    def _sleep_for_retry(self, retry_after: float | None, attempt: int) -> None:
        delay = retry_after if retry_after is not None else min(2**attempt, 30)
        if delay > 0:
            time.sleep(delay)


def _clean_subreddit_name(value: str) -> str:
    name = value.strip()
    if name.startswith("r/"):
        name = name[2:]
    if not name or "/" in name:
        raise ValueError("subreddit name must be a non-empty name without slashes.")
    return name


def _cap_limit(value: int, *, minimum: int, maximum: int) -> int:
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def _permalink_to_json_path(permalink: str) -> str:
    path = permalink.strip()
    if not path:
        raise ValueError("permalink must be a non-empty string.")
    if path.startswith("http://") or path.startswith("https://"):
        path = "/" + path.split("://", 1)[1].split("/", 1)[1]
    if "?" in path:
        path = path.split("?", 1)[0]
    path = path.rstrip("/")
    if not path.endswith(".json"):
        path = f"{path}.json"
    return path


def _headers_to_dict(headers: Any) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _parse_rate_limit(headers: dict[str, str]) -> RateLimitInfo:
    return RateLimitInfo(
        used=_parse_float(headers.get("x-ratelimit-used")),
        remaining=_parse_float(headers.get("x-ratelimit-remaining")),
        reset_seconds=_parse_float(headers.get("x-ratelimit-reset")),
    )


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None
