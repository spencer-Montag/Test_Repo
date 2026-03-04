"""
main.py — Entry point for the GitHub PR analysis tool.

Usage:
    GITHUB_TOKEN=... GITHUB_REPO_OWNER=... GITHUB_REPO_NAME=... python main.py

Optional env vars:
    LOG_LEVEL   — DEBUG | INFO | WARNING (default: INFO)
    OUTPUT_FILE — path to write JSON output (default: prs.json)
"""

from __future__ import annotations

import json
import logging
import os
import sys

from pathlib import Path

from config import load_config
from client import GitHubClient
from gh_types import PullRequest
from exporter import export_to_csv 
from datetime import datetime

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Analysis stubs (expand these in future passes)
# ---------------------------------------------------------------------------

def enrich_pr(pr: PullRequest, client: GitHubClient) -> PullRequest:
    """
    Placeholder for future enrichment passes:
      - Fetch reviews → determine code_owner / non_code_owner
      - Fetch timeline events → determine who assigned and when
    """
    # Example future call:
    # reviews = list(client.iter_pr_reviews(pr["number"]))
    # pr["code_owner"] = determine_code_owner(reviews)
    return pr


def summarize(prs: list[PullRequest]) -> dict[str, int]:
    """Produce a lightweight summary dict for logging / quick inspection."""
    merged = [pr for pr in prs if pr["merged_at"] is not None]
    open_prs = [pr for pr in prs if pr["raw"]["state"] == "open"]
    closed_unmerged = [
        pr for pr in prs
        if pr["raw"]["state"] == "closed" and pr["merged_at"] is None
    ]

    return {
        "total": len(prs),
        "merged": len(merged),
        "open": len(open_prs),
        "closed_unmerged": len(closed_unmerged),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    while True:  

        try: 
            choice = input('(W) to Over-Write to existing (N) create new files').strip()

            if(choice not in ('W','N')):
                raise ValueError(f"Invalid choice: {choice!r}. Enter 'W' or 'N'.")
            break
        except ValueError as exc:
            logger.error("Missing apend file input: %s", exc)
    #end input while


    print('Loading Confing Information')
    try:
        config = load_config()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)


    output_path = Path(os.environ.get("OUTPUT_PATH", "File_Storage"))
    output_path.mkdir(parents=True, exist_ok=True)

    if(choice == 'W'):
        json_path = output_path / "prs.json"
        csv_path = output_path / "prs.csv"
    else:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        json_path = output_path / f"prs_{stamp}.json"
        csv_path  = output_path / f"prs_{stamp}.csv"
        
    #endif 

    logger.info(
        "Starting PR fetch for %s/%s",
        config.repo_owner,
        config.repo_name,
    )

    client = GitHubClient(config)
    prs: list[PullRequest] = []

    try:
        for pr in client.iter_pull_requests(state="all"):
            pr = enrich_pr(pr, client)
            prs.append(pr)
    except Exception as exc:
        logger.error("Fatal error during fetch: %s", exc, exc_info=True)
        sys.exit(1)

    summary = summarize(prs)
    logger.info("Summary: %s", summary)

    # Persist to JSON
    # We cast `raw` (RawPullRequest TypedDict) to dict for json.dumps
    json_path.write_text(
        json.dumps(prs, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Wrote %d PRs to %s", len(prs), json_path)

    # csv_path = GitHub_rpt/File_Storage.with_suffix
    csv_path = json_path.with_suffix(".csv")
    export_to_csv(prs, csv_path)


if __name__ == "__main__":
    main()