"""Configuration loading for BRE.

Searches for bre.yaml in multiple locations, merges with env var overrides.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TwitterAuth:
    auth_token: str = ""
    ct0: str = ""
    # Public bearer token used by X's web client — not a secret
    bearer_token: str = (
        "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
        "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
    )


@dataclass
class FolderConfig:
    id: str
    tag: str


@dataclass
class VaultPaths:
    """Paths to vault files that the skill reads/writes."""
    inbox: Path = Path("bookmarks/inbox.md")
    guidance: Path = Path("bookmarks/bookmark-review-guidance.md")
    triage_dir: Path = Path("bookmarks/triage")
    reports_dir: Path = Path("bookmarks/reports")
    engagement_log: Path = Path("bookmarks/engagement-log.md")
    triage_log: Path = Path("bookmarks/triage-log.md")
    feedback_dir: Path = Path("bookmarks/feedback")
    archive_dir: Path = Path("bookmarks/archive")


@dataclass
class Config:
    auth: TwitterAuth = field(default_factory=TwitterAuth)
    folders: list[FolderConfig] = field(default_factory=list)
    archive_file: Path = Path("~/.config/bre/vault/bookmarks/inbox.md")
    pending_file: Path = Path("~/.config/bre/state/pending-bookmarks.json")
    state_file: Path = Path("~/.config/bre/state/bookmarks-state.json")
    timezone: str = "America/New_York"
    query_ids_cache: Path = Path("~/.config/bre/query-ids.json")
    vault_root: Path = Path("~/.config/bre/vault")
    vault: VaultPaths = field(default_factory=VaultPaths)


CONFIG_SEARCH_PATHS = [
    Path("./bre.yaml"),
    Path("~/.config/bre/config.yaml"),
]


def _expand(p: Path) -> Path:
    return Path(os.path.expanduser(p))


def load_config(path: str | Path | None = None) -> Config:
    """Load config from YAML file + env var overrides.

    Search order:
    1. Explicit path argument
    2. ./bre.yaml
    3. ~/.config/bre/config.yaml
    4. Env var overrides always applied on top
    """
    raw: dict = {}
    search = [Path(path)] if path else CONFIG_SEARCH_PATHS

    for loc in search:
        expanded = _expand(loc)
        if expanded.is_file():
            raw = yaml.safe_load(expanded.read_text()) or {}
            break

    # Build auth
    auth_raw = raw.get("auth", {})
    auth = TwitterAuth(
        auth_token=os.environ.get("BRE_AUTH_TOKEN", auth_raw.get("auth_token", "")),
        ct0=os.environ.get("BRE_CT0", auth_raw.get("ct0", "")),
        bearer_token=auth_raw.get("bearer_token", TwitterAuth.bearer_token),
    )

    # Build folders
    folders_raw = raw.get("folders", {})
    folders = [FolderConfig(id=str(k), tag=v) for k, v in folders_raw.items()]

    # Build vault paths
    vault_root = _expand(Path(raw.get("vault_root", Config.vault_root)))
    vault_raw = raw.get("vault", {})
    vault = VaultPaths(
        inbox=vault_root / vault_raw.get("inbox", VaultPaths.inbox),
        guidance=vault_root / vault_raw.get("guidance", VaultPaths.guidance),
        triage_dir=vault_root / vault_raw.get("triage_dir", VaultPaths.triage_dir),
        reports_dir=vault_root / vault_raw.get("reports_dir", VaultPaths.reports_dir),
        engagement_log=vault_root / vault_raw.get("engagement_log", VaultPaths.engagement_log),
        triage_log=vault_root / vault_raw.get("triage_log", VaultPaths.triage_log),
        feedback_dir=vault_root / vault_raw.get("feedback_dir", VaultPaths.feedback_dir),
        archive_dir=vault_root / vault_raw.get("archive_dir", VaultPaths.archive_dir),
    )

    # Build paths — expand ~ in all
    cfg = Config(
        auth=auth,
        folders=folders,
        archive_file=_expand(Path(raw.get("archive_file", Config.archive_file))),
        pending_file=_expand(Path(raw.get("pending_file", Config.pending_file))),
        state_file=_expand(Path(raw.get("state_file", Config.state_file))),
        timezone=raw.get("timezone", Config.timezone),
        query_ids_cache=_expand(Path(raw.get("query_ids_cache", Config.query_ids_cache))),
        vault_root=vault_root,
        vault=vault,
    )

    return cfg
