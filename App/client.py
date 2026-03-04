"""
client.py — GitHub API client.
Responsible solely for fetching data; no business logic lives here.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator, cast

from config import Config
from gh_types import PullRequest, RawPullRequest
from utils import safe_request, normalize_pr, parse_next_url

logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Thin, stateless wrapper around the GitHub REST API.

    Each public method is a generator that yields individual records so
    callers can start processing before all pages are downloaded.
    """

    def __init__(self, config: Config) -> None:
        self._config = config

    # ------------------------------------------------------------------
    # Pull Requests
    # ------------------------------------------------------------------

    def iter_pull_requests(
        self,
        state: str = "all",
    ) -> Iterator[PullRequest]:
        """
        Yield every pull request for the configured repository.

        Handles pagination transparently; follows GitHub's `Link` header
        until there are no more pages.

        Args:
            state: "open" | "closed" | "all"  (default: "all")
        """
        url: str | None = self._config.repo_pulls_url
        params: dict[str, str | int] = {
            "state": state,
            "per_page": self._config.per_page,
            "page": 1,
        }
        page = 1
        total_fetched = 0

        while url is not None:
            logger.info("Fetching PR page %d from %s", page, url)

            response = safe_request(
                method="GET",
                url=url,
                config=self._config,
                params=params if page == 1 else None,  # params encoded in url after page 1
            )

            payload = response.json()

            if not isinstance(payload, list):
                raise ValueError(
                    f"Expected list from GitHub API, got {type(payload).__name__}: "
                    f"{str(payload)[:200]}"
                )

            typed_payload = cast(list[RawPullRequest], payload)

            if not typed_payload:
                logger.info("Empty page — pagination complete.")
                break

            for raw_pr in typed_payload:
                normalized = normalize_pr(raw_pr)
                total_fetched += 1
                yield normalized

            logger.info("Page %d: yielded %d PRs (total so far: %d)", page, len(typed_payload), total_fetched)

            link_header = response.headers.get("Link", "")
            next_url = parse_next_url(link_header) if link_header else None
            url = next_url
            page += 1
            params = {}  # params are now baked into the next URL

        logger.info("Finished fetching PRs. Total: %d", total_fetched)

    # ------------------------------------------------------------------
    # Future expansion hooks (stubs — wire up when needed)
    # ------------------------------------------------------------------

    def iter_pr_reviews(self, pr_number: int) -> Iterator[dict[str, Any]]:
        """
        Yield all reviews for a single PR.
        Stub — implement when building the review/ownership analysis pass.
        """
        url: str | None = (
            f"{self._config.base_url}/repos/"
            f"{self._config.repo_owner}/{self._config.repo_name}"
            f"/pulls/{pr_number}/reviews"
        )
        params: dict[str, str | int] = {"per_page": self._config.per_page}
        page = 1

        while url is not None:
            response = safe_request("GET", url, self._config, params if page == 1 else None)
            payload = response.json()

            if not isinstance(payload, list):
                raise ValueError(f"Expected list for PR reviews, got {type(payload).__name__}")

            if not payload:
                break

            yield from payload

            link_header = response.headers.get("Link", "")
            url = parse_next_url(link_header) if link_header else None
            page += 1
            params = {}

    def iter_pr_timeline(self, pr_number: int) -> Iterator[dict[str, Any]]:
        """
        Yield all timeline events for a single PR.
        Stub — implement when building assignment-tracking logic.

        Note: Requires the `application/vnd.github.mockingbird-preview` Accept header.
        """
        url: str | None = (
            f"{self._config.base_url}/repos/"
            f"{self._config.repo_owner}/{self._config.repo_name}"
            f"/issues/{pr_number}/timeline"
        )
        params: dict[str, str | int] = {"per_page": self._config.per_page}
        page = 1

        while url is not None:
            response = safe_request("GET", url, self._config, params if page == 1 else None)
            payload = response.json()

            if not isinstance(payload, list):
                raise ValueError(f"Expected list for PR timeline, got {type(payload).__name__}")

            if not payload:
                break

            yield from payload

            link_header = response.headers.get("Link", "")
            url = parse_next_url(link_header) if link_header else None
            page += 1
            params = {}