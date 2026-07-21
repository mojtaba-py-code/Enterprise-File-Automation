"""Copy the finished artifact into the backup directory.

Runs last in the default pipeline so the backup is a snapshot of the fully
processed file. Backups are organised into per-category sub-folders.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import ClassVar

from ..config import AppConfig, BackupConfig
from ..exceptions import ProcessorError
from ..models import FileContext
from .base import Processor


class BackupProcessor(Processor):
    name: ClassVar[str] = "backup"

    def __init__(self, cfg: BackupConfig, backup_dir: Path) -> None:
        super().__init__()
        self._cfg = cfg
        self._backup_dir = backup_dir

    @classmethod
    def from_config(cls, cfg: AppConfig) -> BackupProcessor:
        return cls(cfg.backup, cfg.paths.backup)

    @property
    def enabled(self) -> bool:
        return self._cfg.enabled

    def process(self, ctx: FileContext) -> FileContext:
        target_dir = self._backup_dir / _safe_dir(ctx.category)
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = _unique(target_dir / ctx.working_path.name)
        try:
            shutil.copy2(ctx.working_path, destination)
        except OSError as exc:
            raise ProcessorError(
                self.name, f"cannot back up {ctx.working_path.name}: {exc}"
            ) from exc
        ctx.record_step(self.name, backup=str(destination))
        self.log.debug("backed up to %s", destination)
        return ctx


def _safe_dir(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
    return cleaned or "misc"


def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
