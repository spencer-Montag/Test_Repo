"""
exporter.py — Flatten PullRequest records and export to CSV.

Keeps all export logic isolated from fetching and normalization.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import TypedDict

from gh_types import PullRequest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Defines what a flatPullRequest is  
# ---------------------------------------------------------------------------

class FlatPullRequest(TypedDict):
    id: int
    number: int
    title: str
    body: str
    user: str
    assignees: str          # comma-joined logins
    requested_reviewers: str  # comma-joined logins
    created_at: str
    merged_at: str          # empty string if None
    state: str
    html_url: str
    draft: str              # BOOL
    code_owner: str         # Need to add seperate list of codeowners to assigne these values
    non_code_owner: str     


# HEADER ROW CREATE
CSV_COLUMNS: list[str] = list(FlatPullRequest.__annotations__.keys())


# ---------------------------------------------------------------------------
# Flatten a single PR
# ---------------------------------------------------------------------------

def flatten_pr(pr: PullRequest) -> FlatPullRequest:
    """
    Convert a nested PullRequest into a flat CSV-ready row.

    Rules:
      - list fields   → comma-joined string  e.g. "alice, bob"
      - None fields   → empty string
      - bool fields   → "true" / "false"
      - raw fields    → pulled directly from pr["raw"] where needed
    """
    raw = pr["raw"]

    return FlatPullRequest(
        id=pr["id"],
        number=pr["number"],
        title=pr["title"],
        body=pr["body"] or "",
        user=pr["user"],
        assignees=", ".join(pr["assignees"]),
        requested_reviewers=", ".join(pr["requested_reviewers"]),
        created_at=pr["created_at"],
        merged_at=pr["merged_at"] or "",
        state=raw["state"],
        html_url=raw.get("html_url", ""),
        draft="true" if raw.get("draft") else "false",
        code_owner=pr["code_owner"] or "",
        non_code_owner=pr["non_code_owner"] or "",
    )


# ---------------------------------------------------------------------------
# Export to CSV
# ---------------------------------------------------------------------------

def export_to_csv(prs: list[PullRequest], output_path: Path) -> None:
    """
    Flatten all PRs and write them to a CSV file.

    Args:
        prs:         List of normalized PullRequest records.
        output_path: Destination .csv file path.
    """
    if not prs:
        logger.warning("No PRs to export — skipping CSV write.")
        return

    rows = [flatten_pr(pr) for pr in prs]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)  # type: ignore[arg-type]

    logger.info("Exported %d rows to %s", len(rows), output_path)