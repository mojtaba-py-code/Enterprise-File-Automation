"""Pipeline processors and the factory that builds them from config."""

from __future__ import annotations

from ..config import AppConfig
from .backup import BackupProcessor
from .base import Processor
from .classifier import ClassifyProcessor
from .compressor import CompressProcessor
from .converter import ConvertProcessor
from .encryptor import EncryptProcessor
from .renamer import RenameProcessor

__all__ = [
    "BackupProcessor",
    "ClassifyProcessor",
    "CompressProcessor",
    "ConvertProcessor",
    "EncryptProcessor",
    "Processor",
    "RenameProcessor",
    "build_processors",
]


def build_processors(cfg: AppConfig) -> list[Processor]:
    """Instantiate the processors named in ``cfg.pipeline``, in order.

    Steps whose section is disabled are still created but become no-ops at
    runtime (they report themselves as skipped), keeping the pipeline order
    declarative and the config the single source of truth.
    """
    factories: dict[str, type[Processor]] = {
        "classify": ClassifyProcessor,
        "convert": ConvertProcessor,
        "rename": RenameProcessor,
        "compress": CompressProcessor,
        "encrypt": EncryptProcessor,
        "backup": BackupProcessor,
    }
    return [factories[name].from_config(cfg) for name in cfg.pipeline]
