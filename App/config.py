"""
config.py — Central configuration for the GitHub PR analysis tool.
All environment-driven settings live here.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # loads .env into os.environ before anything reads it


@dataclass(frozen=True)
class Config:
    github_token: str
    repo_owner: str
    repo_name: str

    # Pagination
    per_page: int = 100

    # Retry / backoff
    max_retries: int = 5
    backoff_base: float = 1.0       # seconds; doubles each attempt
    backoff_max: float = 60.0       # cap on wait time

    # HTTP
    timeout: int = 18              # seconds per request

    @property
    def base_url(self) -> str:
        return "https://api.github.com"

    @property
    def repo_pulls_url(self) -> str:
        return f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls"

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }


def load_config() -> Config:
    """
    Load configuration from environment variables.
    Raises ValueError for any missing required variable.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    owner = os.environ.get("GITHUB_REPO_OWNER", "")
    name = os.environ.get("GITHUB_REPO_NAME", "")

    missing = [k for k, v in [
        ("GITHUB_TOKEN", token),
        ("GITHUB_REPO_OWNER", owner),
        ("GITHUB_REPO_NAME", name),
    ] if not v]

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        github_token=token,
        repo_owner=owner,
        repo_name=name,
    )