"""Tests for the persistent state store."""

from __future__ import annotations

from pathlib import Path

import pytest

from file_automation.exceptions import StateError
from file_automation.models import ProcessResult
from file_automation.state import StateStore


def _result(status: str, file_hash: str = "abc123") -> ProcessResult:
    return ProcessResult(
        source_path=Path("in/x.txt"),
        status=status,  # type: ignore[arg-type]
        original_hash=file_hash,
        category="documents",
    )


def test_new_hash_should_process(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.load()
    assert store.should_process("newhash") is True


def test_success_not_reprocessed(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.load()
    store.record(_result("success"))
    assert store.should_process("abc123") is False


def test_failure_retried_until_limit(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json", max_retries=2)
    store.load()
    store.record(_result("failed"))
    assert store.should_process("abc123") is True  # 1 attempt < 2
    store.record(_result("failed"))
    assert store.should_process("abc123") is False  # 2 attempts == limit


def test_attempts_increment(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.load()
    store.record(_result("failed"))
    store.record(_result("failed"))
    assert store.attempts_for("abc123") == 2


def test_persist_and_reload(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.load()
    store.record(_result("success"))
    store.save()

    reloaded = StateStore(path)
    reloaded.load()
    assert reloaded.should_process("abc123") is False
    assert len(reloaded) == 1


def test_atomic_save_leaves_no_tmp(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.load()
    store.record(_result("success"))
    store.save()
    assert not (tmp_path / "state.json.tmp").exists()


def test_use_before_load_errors(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    with pytest.raises(StateError, match="load"):
        store.should_process("x")


def test_corrupt_state_file_errors(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("not json {", encoding="utf-8")
    store = StateStore(path)
    with pytest.raises(StateError, match="cannot read"):
        store.load()
