"""Tests for configuration parsing and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from file_automation.config import from_mapping, load_config
from file_automation.exceptions import ConfigError


def test_parses_full_config(config_dict: dict[str, Any], tmp_path: Path) -> None:
    cfg = from_mapping(config_dict, base_dir=tmp_path)
    assert cfg.pipeline == ("classify", "rename", "compress", "backup")
    assert cfg.classify.ext_to_category[".txt"] == "documents"
    assert cfg.max_retries == 2
    assert cfg.paths.inbox == tmp_path / "inbox"


def test_relative_paths_resolved_against_base(tmp_path: Path) -> None:
    data = {"paths": {"inbox": "./in"}, "pipeline": ["classify"]}
    cfg = from_mapping(data, base_dir=tmp_path)
    assert cfg.paths.inbox == tmp_path / "in"


def test_unknown_pipeline_step_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="unknown pipeline step"):
        from_mapping({"pipeline": ["nope"]}, base_dir=tmp_path)


def test_duplicate_pipeline_step_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="more than once"):
        from_mapping({"pipeline": ["classify", "classify"]}, base_dir=tmp_path)


def test_empty_pipeline_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="non-empty list"):
        from_mapping({"pipeline": []}, base_dir=tmp_path)


def test_conflicting_extension_mapping_rejected(tmp_path: Path) -> None:
    data = {
        "pipeline": ["classify"],
        "classify": {"rules": {"a": [".txt"], "b": [".txt"]}},
    }
    with pytest.raises(ConfigError, match="mapped to both"):
        from_mapping(data, base_dir=tmp_path)


def test_bad_compress_format_rejected(tmp_path: Path) -> None:
    data = {"pipeline": ["compress"], "compress": {"format": "rar"}}
    with pytest.raises(ConfigError, match=r"compress\.format"):
        from_mapping(data, base_dir=tmp_path)


def test_email_enabled_requires_fields(tmp_path: Path) -> None:
    data = {"pipeline": ["classify"], "email": {"enabled": True}}
    with pytest.raises(ConfigError, match=r"email\.enabled is true"):
        from_mapping(data, base_dir=tmp_path)


def test_bad_log_level_rejected(tmp_path: Path) -> None:
    data = {"pipeline": ["classify"], "logging": {"level": "LOUD"}}
    with pytest.raises(ConfigError, match=r"logging\.level"):
        from_mapping(data, base_dir=tmp_path)


def test_extension_normalization(tmp_path: Path) -> None:
    data = {
        "pipeline": ["classify"],
        "classify": {"rules": {"docs": ["txt", ".MD"]}},
    }
    cfg = from_mapping(data, base_dir=tmp_path)
    assert cfg.classify.ext_to_category[".txt"] == "docs"
    assert cfg.classify.ext_to_category[".md"] == "docs"


def test_load_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_load_config_roundtrip(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "pipeline: [classify]\npaths: {inbox: ./inbox}\n", encoding="utf-8"
    )
    # Relative paths resolve against base_dir (defaults to CWD).
    cfg = load_config(cfg_file, base_dir=tmp_path)
    assert cfg.paths.inbox == tmp_path / "inbox"


def test_load_config_resolves_against_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    work = tmp_path / "work"
    work.mkdir()
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("pipeline: [classify]\npaths: {inbox: ./inbox}\n", encoding="utf-8")
    monkeypatch.chdir(work)
    cfg = load_config(cfg_file)
    assert cfg.paths.inbox == work / "inbox"


def test_empty_config_file_rejected(tmp_path: Path) -> None:
    cfg_file = tmp_path / "empty.yaml"
    cfg_file.write_text("", encoding="utf-8")
    with pytest.raises(ConfigError, match="empty"):
        load_config(cfg_file)
