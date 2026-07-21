"""The processor contract shared by every pipeline step.

A processor takes a :class:`~file_automation.models.FileContext`, does one job,
and returns the (possibly mutated) context. Transforming processors rewrite
``ctx.working_path``; annotating processors (classify) only set fields. On an
unrecoverable problem a processor raises
:class:`~file_automation.exceptions.ProcessorError`, which the pipeline catches
to fail just that one file.

This uniform interface is what lets the pipeline stay ignorant of any specific
step: adding a capability later is a new subclass plus one config entry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from ..config import AppConfig
from ..logger import get_logger
from ..models import FileContext


class Processor(ABC):
    """Abstract base class for all pipeline steps."""

    #: Stable identifier, also used as the config/pipeline step name.
    name: ClassVar[str]

    def __init__(self) -> None:
        self.log = get_logger(self.name)

    @classmethod
    @abstractmethod
    def from_config(cls, cfg: AppConfig) -> Processor:
        """Build the processor from the application configuration."""

    @property
    def enabled(self) -> bool:
        """Whether this step does real work; disabled steps are skipped."""
        return True

    @abstractmethod
    def process(self, ctx: FileContext) -> FileContext:
        """Run the step and return the updated context."""

    def run(self, ctx: FileContext) -> FileContext:
        """Wrapper used by the pipeline: honours the ``enabled`` flag."""
        if not self.enabled:
            self.log.debug("skipped (disabled): %s", ctx.working_path.name)
            return ctx
        return self.process(ctx)
