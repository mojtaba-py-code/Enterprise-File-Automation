"""Classify a file into a category based on its extension."""

from __future__ import annotations

from typing import ClassVar

from ..config import AppConfig, ClassifyConfig
from ..models import FileContext
from .base import Processor


class ClassifyProcessor(Processor):
    name: ClassVar[str] = "classify"

    def __init__(self, cfg: ClassifyConfig) -> None:
        super().__init__()
        self._cfg = cfg

    @classmethod
    def from_config(cls, cfg: AppConfig) -> ClassifyProcessor:
        return cls(cfg.classify)

    def process(self, ctx: FileContext) -> FileContext:
        ext = ctx.source_path.suffix.lower()
        category = self._cfg.ext_to_category.get(ext, self._cfg.default_category)
        ctx.category = category
        ctx.record_step(self.name, category=category)
        self.log.debug("%s -> %s", ctx.source_path.name, category)
        return ctx
