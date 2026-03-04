"""
utils.py — Pure utility functions with no external state.
"""

from __future__ import annotations

import logging
import time

import requests

from config import Config
from gh_types import RawPullRequest, PullRequest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def safe_request(
    method: str,
    url: str,
    config: Config,
    params: dict[str, str | int] | None = None,
) -> requests.Response:
    """
    Execute an HTTP request with exponential-backoff retry.

    Guarantees: always returns a `requests.Response` with status < 400,
    or raises an exception.  Never returns None implicitly.

    Retries on:
      - Connection / timeout errors
      - 429 (rate limited) and 5xx server errors

    Raises:
      - requests.HTTPError  for non-retryable 4xx responses
      - requests.RequestException  after exhausting retries
    """
    attempt = 0
    last_exc: Exception | None = None

    while attempt <= config.max_retries:
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=config.auth_headers,
                params=params,
                timeout=config.timeout,
            )

            # Non-retryable client errors — fail immediately
            if 400 <= response.status_code < 500 and response.status_code != 429:
                logger.error(
                    "Client error %s for %s: %s",
                    response.status_code, url, response.text[:200],
                )
                response.raise_for_status()

            # Retryable: rate-limited or server error
            if response.status_code == 429 or response.status_code >= 500:
                wait = _backoff_wait(attempt, config)
                logger.warning(
                    "Retryable status %s on attempt %d/%d — waiting %.1fs",
                    response.status_code, attempt + 1, config.max_retries, wait,
                )
                time.sleep(wait)
                attempt += 1
                continue

            # Success
            return response

        except requests.exceptions.RequestException as exc:
            last_exc = exc
            wait = _backoff_wait(attempt, config)
            logger.warning(
                "Request error on attempt %d/%d (%s) — retrying in %.1fs",
                attempt + 1, config.max_retries, exc, wait,
            )
            time.sleep(wait)
            attempt += 1

    raise requests.exceptions.RetryError(
        f"Exhausted {config.max_retries} retries for {url}"
    ) from last_exc


def _backoff_wait(attempt: int, config: Config) -> float:
    """Return capped exponential backoff duration for the given attempt index."""
    wait = config.backoff_base * (2 ** attempt)
    return min(wait, config.backoff_max)


# ---------------------------------------------------------------------------
# PR normalization
# ---------------------------------------------------------------------------

def normalize_pr(raw: RawPullRequest) -> PullRequest:
    """
    Translate a raw GitHub API payload into our typed PullRequest model.
    """
    return PullRequest(
        id=raw["id"],
        number=raw["number"],
        title=raw["title"],
        body=raw.get("body"),
        user=raw["user"]["login"],
        assignees=[a["login"] for a in raw.get("assignees", [])],
        requested_reviewers=[r["login"] for r in raw.get("requested_reviewers", [])],
        created_at=raw["created_at"],
        merged_at=raw.get("merged_at"),
        code_owner=None,
        non_code_owner=None,
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Pagination helpers
# ---------------------------------------------------------------------------

def parse_next_url(link_header: str) -> str | None:
    """
    Parse GitHub's `Link` response header and return the 'next' page URL,
    or None if this is the last page.

    Example header value:
      <https://api.github.com/...?page=2>; rel="next", <...>; rel="last"
    """
    for part in link_header.split(","):
        url_part, _, rel_part = part.strip().partition(";")
        if rel_part.strip() == 'rel="next"':
            return url_part.strip().lstrip("<").rstrip(">")
    return None