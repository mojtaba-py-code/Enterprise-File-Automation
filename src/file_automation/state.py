"""Persistent processing state (``state.json``).

Entries are keyed by the file's SHA-256 hash, so:

* an unchanged file is never processed twice,
* an edited file (new content -> new hash) is treated as new work,
* a file that keeps failing is retried up to ``max_retries`` times and then
  permanently skipped, preventing infinite retry loops.

Writes are atomic (temp file + ``os.replace``) so a crash mid-write cannot
corrupt the state file.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .exceptions import StateError
from .models import ProcessResult

_SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class StateStore:
    """Load, query and persist per-file processing state."""

    def __init__(self, path: Path, *, max_retries: int = 3) -> None:
        self._path = path
        self._max_retries = max_retries
        self._entries: dict[str, dict[str, Any]] = {}
        self._loaded = False

    # -- persistence -------------------------------------------------------- #
    def load(self) -> None:
        """Load state from disk. A missing file starts an empty state."""
        if not self._path.exists():
            self._entries = {}
            self._loaded = True
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f"cannot read state file {self._path}: {exc}") from exc
        if not isinstance(data, dict):
            raise StateError(f"state file {self._path} is not a JSON object")
        entries = data.get("entries", {})
        if not isinstance(entries, dict):
            raise StateError(f"state file {self._path} has a malformed 'entries' section")
        self._entries = entries
        self._loaded = True

    def save(self) -> None:
        """Atomically write state to disk."""
        payload = {
            "version": _SCHEMA_VERSION,
            "updated": _now_iso(),
            "entries": self._entries,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self._path)
        except OSError as exc:
            raise StateError(f"cannot write state file {self._path}: {exc}") from exc
        finally:
            tmp.unlink(missing_ok=True)

    # -- queries ------------------------------------------------------------ #
    def _ensure_loaded(self) -> None:
        if not self._loaded:
            raise StateError("StateStore.load() must be called before use")

    def should_process(self, file_hash: str) -> bool:
        """True if a file with this hash still needs processing.

        Files already succeeded, or failed past ``max_retries``, are skipped.
        """
        self._ensure_loaded()
        entry = self._entries.get(file_hash)
        if entry is None:
            return True
        if entry.get("status") == "success":
            return False
        attempts = int(entry.get("attempts", 0))
        return attempts < self._max_retries

    def attempts_for(self, file_hash: str) -> int:
        self._ensure_loaded()
        entry = self._entries.get(file_hash)
        return int(entry.get("attempts", 0)) if entry else 0

    # -- mutation ----------------------------------------------------------- #
    def record(self, result: ProcessResult) -> None:
        """Record the outcome of a processing attempt."""
        self._ensure_loaded()
        previous = self._entries.get(result.original_hash, {})
        attempts = int(previous.get("attempts", 0)) + 1
        self._entries[result.original_hash] = {
            "path": str(result.source_path),
            "status": result.status,
            "category": result.category,
            "output": str(result.output_path) if result.output_path else None,
            "steps": list(result.steps),
            "error": result.error,
            "attempts": attempts,
            "updated": _now_iso(),
        }

    def __len__(self) -> int:
        return len(self._entries)
