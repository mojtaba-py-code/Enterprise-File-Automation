"""Encrypt the working file with Fernet (AES-128-CBC + HMAC).

The key is read from an environment variable named in the config; it is never
stored in the config file or the repository. Encryption runs last (after
compression) because encrypted bytes are effectively incompressible.
"""

from __future__ import annotations

import os
from typing import ClassVar

from ..config import AppConfig, EncryptConfig
from ..exceptions import ProcessorError
from ..models import FileContext
from .base import Processor

_ENCRYPTED_SUFFIX = ".enc"


class EncryptProcessor(Processor):
    name: ClassVar[str] = "encrypt"

    def __init__(self, cfg: EncryptConfig) -> None:
        super().__init__()
        self._cfg = cfg

    @classmethod
    def from_config(cls, cfg: AppConfig) -> EncryptProcessor:
        return cls(cfg.encrypt)

    @property
    def enabled(self) -> bool:
        return self._cfg.enabled

    def _load_cipher(self) -> object:
        try:
            from cryptography.fernet import Fernet
        except ImportError as exc:  # pragma: no cover - dependency guaranteed by install
            raise ProcessorError(self.name, "cryptography is required for encryption") from exc

        key = os.environ.get(self._cfg.key_env)
        if not key:
            raise ProcessorError(
                self.name,
                f"encryption key not found in environment variable '{self._cfg.key_env}'",
            )
        try:
            return Fernet(key.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise ProcessorError(
                self.name, f"invalid Fernet key in '{self._cfg.key_env}': {exc}"
            ) from exc

    def process(self, ctx: FileContext) -> FileContext:
        cipher = self._load_cipher()
        working = ctx.working_path
        destination = working.with_name(working.name + _ENCRYPTED_SUFFIX)
        try:
            data = working.read_bytes()
            token = cipher.encrypt(data)  # type: ignore[attr-defined]
            destination.write_bytes(token)
        except OSError as exc:
            destination.unlink(missing_ok=True)
            raise ProcessorError(self.name, f"cannot encrypt {working.name}: {exc}") from exc

        working.unlink(missing_ok=True)
        ctx.record_step(self.name, encrypted=destination.name)
        ctx.working_path = destination
        self.log.debug("encrypted %s", destination.name)
        return ctx

    @staticmethod
    def generate_key() -> str:
        """Generate a fresh Fernet key (used by the ``keygen`` CLI command)."""
        from cryptography.fernet import Fernet

        return Fernet.generate_key().decode("utf-8")
