"""File hashing utilities used for change detection."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK = 1 << 20  # 1 MiB


def sha256_of(path: Path) -> str:
    """Return the hex SHA-256 digest of a file, read in chunks.

    Content-based hashing means an edited file (same name, new content) is
    treated as new work, while an unchanged file is never reprocessed.
    """
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()
