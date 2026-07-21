"""Exception hierarchy for the file-automation package.

A single base class (:class:`FileAutomationError`) lets callers catch every
error raised by this package, while the subclasses allow precise handling.
"""

from __future__ import annotations


class FileAutomationError(Exception):
    """Base class for all errors raised by this package."""


class ConfigError(FileAutomationError):
    """Raised when the configuration is missing, malformed or invalid."""


class ProcessorError(FileAutomationError):
    """Raised by a pipeline processor when it cannot process a file.

    Carries the name of the processor that failed so the pipeline can report
    exactly where a file broke.
    """

    def __init__(self, processor: str, message: str) -> None:
        self.processor = processor
        super().__init__(f"[{processor}] {message}")


class StateError(FileAutomationError):
    """Raised when the persistent state file cannot be read or written."""
