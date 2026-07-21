"""Compress the working file into a ZIP archive."""

from __future__ import annotations

import zipfile
from typing import ClassVar

from ..config import AppConfig, CompressConfig
from ..exceptions import ProcessorError
from ..models import FileContext
from .base import Processor


class CompressProcessor(Processor):
    name: ClassVar[str] = "compress"

    def __init__(self, cfg: CompressConfig) -> None:
        super().__init__()
        self._cfg = cfg

    @classmethod
    def from_config(cls, cfg: AppConfig) -> CompressProcessor:
        return cls(cfg.compress)

    @property
    def enabled(self) -> bool:
        return self._cfg.enabled

    def process(self, ctx: FileContext) -> FileContext:
        working = ctx.working_path
        try:
            size = working.stat().st_size
        except OSError as exc:
            raise ProcessorError(self.name, f"cannot stat {working.name}: {exc}") from exc

        if size < self._cfg.min_size_bytes:
            self.log.debug("skip compress (%d < %d bytes)", size, self._cfg.min_size_bytes)
            return ctx

        archive = working.with_suffix(working.suffix + ".zip")
        try:
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                # arcname without the ".zip" so the entry keeps the real name.
                zf.write(working, arcname=working.name)
        except (OSError, zipfile.BadZipFile) as exc:
            archive.unlink(missing_ok=True)
            raise ProcessorError(self.name, f"cannot compress {working.name}: {exc}") from exc

        working.unlink(missing_ok=True)
        ctx.record_step(self.name, archive=archive.name, original_size=size)
        ctx.working_path = archive
        self.log.debug("compressed %s (%d bytes)", archive.name, size)
        return ctx
