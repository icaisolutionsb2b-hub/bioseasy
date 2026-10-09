# SPDX-License-Identifier: GPL-3.0-or-later
"""Secrets at rest: the ntfy access token.

Encrypted with Fernet under `<data_dir>/connector.key` (the name it has always had), created on
first use with mode 0600 and kept apart from the database file. Honest limit: this protects a
copied or shared database file, not an attacker who can already read the whole data volume, since
the key sits right next to the database there.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class SecretError(Exception):
    """A stored secret could not be decrypted (wrong or missing key file, corrupted value)."""


def _load_key(data_dir: Path, create: bool = True) -> bytes:
    """The key, created only when `create` is set.

    The web service and the worker share /data and can both reach this on first use. The key is
    written completely to a private temp file and then hard-linked into place: the link fails if
    another process got there first, and a reader never sees a half-written key file.
    """
    path = data_dir / "connector.key"
    try:
        return path.read_bytes()
    except FileNotFoundError:
        if not create:
            raise
    fd, tmp_name = tempfile.mkstemp(dir=data_dir, prefix=".connector.key.")  # mode 0600
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(Fernet.generate_key())
        try:
            os.link(tmp_name, path)
        except FileExistsError:
            pass  # the other process won; its key is the one everybody uses
    finally:
        os.unlink(tmp_name)
    return path.read_bytes()


def encrypt_secret(data_dir: Path, plaintext: str) -> bytes:
    return Fernet(_load_key(data_dir)).encrypt(plaintext.encode())


def decrypt_secret(data_dir: Path, ciphertext: bytes) -> str:
    # Never creates a key: a fresh key cannot read old ciphertext, and a missing key file must
    # stay visible as an error instead of being silently replaced.
    try:
        return Fernet(_load_key(data_dir, create=False)).decrypt(ciphertext).decode()
    except (InvalidToken, FileNotFoundError) as exc:
        raise SecretError("Stored secret could not be read") from exc
