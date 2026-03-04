"""
types.py — All shared TypedDicts and type aliases for the PR analysis tool.

Compatibility: Python 3.9+
All imports are from the standard `typing` module — no third-party packages needed.

TypedDict pattern used throughout:
  - Required fields declared in a `total=True` base class (the default).
  - Optional *absent* fields declared in a `total=False` subclass.
  - Fields whose value can be None are typed `str | None` (not `Optional`),
    making the nullability explicit and strict-mode friendly.
"""

from __future__ import annotations

from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# GitHubUser
# ---------------------------------------------------------------------------

class GitHubUser(TypedDict):
    """Always present fields on a GitHub user object."""
    login: str
    id: int


class GitHubUserFull(GitHubUser, total=False):
    """Optional fields that may or may not appear."""
    avatar_url: str
    html_url: str


# ---------------------------------------------------------------------------
# GitHubLabel
# ---------------------------------------------------------------------------

class GitHubLabel(TypedDict):
    id: int
    name: str


class GitHubLabelFull(GitHubLabel, total=False):
    color: str
    description: str | None   # present but nullable


# ---------------------------------------------------------------------------
# GitHubMilestone
# ---------------------------------------------------------------------------

class GitHubMilestone(TypedDict):
    id: int
    number: int
    title: str


class GitHubMilestoneFull(GitHubMilestone, total=False):
    state: str


# ---------------------------------------------------------------------------
# RawPullRequest
#
# Split into required (base) + optional (subclass).
# Fields that are present but nullable use `X | None`.
# Fields that may simply be absent live in the `total=False` subclass.
# ---------------------------------------------------------------------------

class _RawPullRequestRequired(TypedDict):
    """Fields guaranteed to be present in every GitHub PR payload."""
    id: int
    number: int
    title: str
    state: str
    user: GitHubUser
    created_at: str


class RawPullRequest(_RawPullRequestRequired, total=False):
    """Full raw GitHub PR payload. Required fields + all optional/nullable ones."""
    body: str | None
    assignees: list[GitHubUser]
    requested_reviewers: list[GitHubUser]
    updated_at: str
    closed_at: str | None
    merged_at: str | None
    merge_commit_sha: str | None
    html_url: str
    labels: list[GitHubLabel]
    milestone: GitHubMilestone | None
    draft: bool
    head: dict[str, Any]
    base: dict[str, Any]


# ---------------------------------------------------------------------------
# PullRequest — our normalized model
# ---------------------------------------------------------------------------

class PullRequest(TypedDict):
    """
    Normalized PR record.

    `raw` preserves the full original API payload so any field can be
    accessed later without a re-fetch.

    `code_owner` and `non_code_owner` are None until the enrichment pass runs.
    """
    id: int
    number: int
    title: str
    body: str | None
    user: str                       # author login
    assignees: list[str]            # logins
    requested_reviewers: list[str]  # logins
    created_at: str
    merged_at: str | None
    code_owner: str | None          # populated in enrichment pass i.e we need to manilpulate data to get what we want 
    non_code_owner: str | None      # populated in enrichment pass
    raw: RawPullRequest


# ---------------------------------------------------------------------------
# Future-facing stubs (wire up when those endpoints are implemented)
# ---------------------------------------------------------------------------

class _ReviewEventRequired(TypedDict):
    id: int
    user: GitHubUser
    state: str        # APPROVED | CHANGES_REQUESTED | COMMENTED
    submitted_at: str


class ReviewEvent(_ReviewEventRequired, total=False):
    """A single PR review from the /pulls/{number}/reviews endpoint."""
    body: str | None


class _TimelineEventRequired(TypedDict):
    event: str        # e.g. "assigned", "review_requested"
    created_at: str


class TimelineEvent(_TimelineEventRequired, total=False):
    """A single PR timeline event from the /issues/{number}/timeline endpoint."""
    id: int
    actor: GitHubUser
    assignee: GitHubUser | None
    requested_reviewer: GitHubUser | None