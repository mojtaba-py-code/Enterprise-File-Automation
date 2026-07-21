"""Core data structures passed between the pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Status = Literal["success", "failed", "skipped"]


@dataclass
class FileContext:
    """Mutable state for a single file travelling through the pipeline.

    ``source_path`` is the untouched original in the inbox. ``working_path``
    starts as a copy in the staging area and is rewritten by processors that
    transform the file (convert, compress, encrypt, rename). Keeping the two
    separate guarantees the inbox is never mutated.
    """

    source_path: Path
    working_path: Path
    original_hash: str
    category: str = "unknown"
    steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_step(self, name: str, **meta: Any) -> None:
        """Mark a processor as applied and merge any metadata it produced."""
        self.steps.append(name)
        if meta:
            self.metadata.setdefault(name, {}).update(meta)


@dataclass
class ProcessResult:
    """Outcome of processing one file, persisted to state and reported."""

    source_path: Path
    status: Status
    original_hash: str
    category: str = "unknown"
    output_path: Path | None = None
    steps: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "success"
