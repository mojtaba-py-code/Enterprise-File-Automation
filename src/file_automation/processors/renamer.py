"""Rename the working file to a standardized, collision-safe name.

The pattern is filled from the file's own attributes (its modification time,
category, original stem, and a short hash) so names are deterministic and
reproducible rather than depending on wall-clock time at processing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from ..config import AppConfig, RenameConfig
from ..exceptions import ProcessorError
from ..models import FileContext
from .base import Processor

# Characters not safe across Windows/POSIX filesystems.
_ILLEGAL = '<>:"/\\|?*'
_ILLEGAL_MAP = {ord(ch): "_" for ch in _ILLEGAL}


def _sanitize(component: str) -> str:
    cleaned = component.translate(_ILLEGAL_MAP).strip(" .")
    return cleaned or "file"


class RenameProcessor(Processor):
    name: ClassVar[str] = "rename"

    def __init__(self, cfg: RenameConfig) -> None:
        super().__init__()
        self._cfg = cfg

    @classmethod
    def from_config(cls, cfg: AppConfig) -> RenameProcessor:
        return cls(cfg.rename)

    @property
    def enabled(self) -> bool:
        return self._cfg.enabled

    def process(self, ctx: FileContext) -> FileContext:
        working = ctx.working_path
        mtime = datetime.fromtimestamp(ctx.source_path.stat().st_mtime, tz=UTC)
        fields = {
            "date": mtime.strftime("%Y-%m-%d"),
            "time": mtime.strftime("%H%M%S"),
            "category": _sanitize(ctx.category),
            "stem": _sanitize(ctx.source_path.stem),
            "ext": working.suffix.lower(),
            "hash8": ctx.original_hash[:8],
        }
        try:
            new_name = self._cfg.pattern.format(**fields)
        except (KeyError, IndexError) as exc:
            raise ProcessorError(self.name, f"invalid rename pattern: {exc}") from exc

        new_name = _sanitize(new_name)
        destination = self._unique(working.with_name(new_name))
        working.rename(destination)
        ctx.record_step(self.name, new_name=destination.name)
        ctx.working_path = destination
        self.log.debug("renamed to %s", destination.name)
        return ctx

    @staticmethod
    def _unique(path: Path) -> Path:
        """Avoid clobbering an existing staging file by appending a counter."""
        if not path.exists():
            return path
        stem, suffix, parent = path.stem, path.suffix, path.parent
        counter = 1
        while True:
            candidate = parent / f"{stem}({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1
