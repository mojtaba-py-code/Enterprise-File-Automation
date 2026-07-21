"""Tests for the command-line interface."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from cryptography.fernet import Fernet

from file_automation.main import main


def _write_config(tmp_path: Path) -> Path:
    data = {
        "pipeline": ["classify", "compress", "backup"],
        "paths": {
            "inbox": str(tmp_path / "inbox"),
            "output": str(tmp_path / "output"),
            "failed": str(tmp_path / "failed"),
            "staging": str(tmp_path / "staging"),
            "backup": str(tmp_path / "backup"),
            "state_file": str(tmp_path / "state.json"),
        },
        "classify": {"rules": {"documents": [".txt"]}},
        "compress": {"enabled": True, "min_size_bytes": 0},
        "encrypt": {"enabled": False},
        "email": {"enabled": False},
        "logging": {"level": "INFO", "console": False},
    }
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    return cfg_file


def test_keygen_prints_valid_key(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["keygen"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert isinstance(Fernet(out.encode()), Fernet)


def test_init_creates_directories(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg_file = _write_config(tmp_path)
    rc = main(["--config", str(cfg_file), "init"])
    assert rc == 0
    assert (tmp_path / "inbox").is_dir()
    assert (tmp_path / "backup").is_dir()


def test_run_once_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg_file = _write_config(tmp_path)
    (tmp_path / "inbox").mkdir()
    (tmp_path / "inbox" / "a.txt").write_text("hello" * 100, encoding="utf-8")

    rc = main(["--config", str(cfg_file), "run-once"])
    assert rc == 0
    assert "Succeeded : 1" in capsys.readouterr().out
    assert list((tmp_path / "output").iterdir())


def test_run_once_reports_failure_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = {
        "pipeline": ["encrypt"],
        "paths": {"inbox": str(tmp_path / "inbox"), "state_file": str(tmp_path / "s.json")},
        "encrypt": {"enabled": True, "key_env": "NOPE_KEY"},
        "logging": {"console": False},
    }
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.delenv("NOPE_KEY", raising=False)
    (tmp_path / "inbox").mkdir()
    (tmp_path / "inbox" / "a.txt").write_text("data", encoding="utf-8")

    rc = main(["--config", str(cfg_file), "run-once"])
    assert rc == 1  # non-zero because a file failed


def test_missing_config_returns_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--config", str(tmp_path / "nope.yaml"), "run-once"])
    assert rc == 2
    assert "error:" in capsys.readouterr().err
