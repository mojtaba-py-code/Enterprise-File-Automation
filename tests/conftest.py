"""Shared fixtures for the test-suite."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from file_automation.config import AppConfig, from_mapping


@pytest.fixture
def config_dict(tmp_path: Path) -> dict[str, Any]:
    """A complete, minimal configuration rooted at a temp directory."""
    return {
        "schedule": {"interval_minutes": 1, "run_immediately": False},
        "max_retries": 2,
        "recursive": True,
        "paths": {
            "inbox": str(tmp_path / "inbox"),
            "output": str(tmp_path / "output"),
            "failed": str(tmp_path / "failed"),
            "staging": str(tmp_path / "staging"),
            "backup": str(tmp_path / "backup"),
            "state_file": str(tmp_path / "state.json"),
        },
        "pipeline": ["classify", "rename", "compress", "backup"],
        "classify": {
            "default_category": "misc",
            "rules": {"documents": [".txt", ".md"], "images": [".png", ".jpg"]},
        },
        "convert": {"enabled": False, "rules": {}},
        "rename": {"enabled": True, "pattern": "{date}_{category}_{stem}_{hash8}{ext}"},
        "compress": {"enabled": True, "format": "zip", "min_size_bytes": 0},
        "encrypt": {"enabled": False, "key_env": "TEST_KEY"},
        "backup": {"enabled": True},
        "email": {"enabled": False},
        "logging": {"level": "DEBUG", "file": None, "console": False},
    }


@pytest.fixture
def make_config(tmp_path: Path) -> Callable[[dict[str, Any]], AppConfig]:
    """Return a factory that turns a config dict into an AppConfig."""

    def _factory(data: dict[str, Any]) -> AppConfig:
        return from_mapping(data, base_dir=tmp_path)

    return _factory


@pytest.fixture
def config(
    config_dict: dict[str, Any],
    make_config: Callable[[dict[str, Any]], AppConfig],
) -> AppConfig:
    return make_config(config_dict)


@pytest.fixture
def sample_file(config: AppConfig) -> Path:
    """A small text file placed in the inbox."""
    config.paths.inbox.mkdir(parents=True, exist_ok=True)
    path = config.paths.inbox / "note.txt"
    path.write_text("hello world\n" * 10, encoding="utf-8")
    return path
