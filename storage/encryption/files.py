"""Authenticated encryption for local recording artifacts."""

import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptedFileStore:
    """Encrypt and decrypt individual files with a caller-managed AES-256 key."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("AES-256 keys must be exactly 32 bytes")
        self._cipher = AESGCM(key)

    def encrypt_file(
        self,
        source: Path,
        destination: Path,
        *,
        associated_data: bytes | None = None,
    ) -> None:
        nonce = os.urandom(12)
        encrypted = self._cipher.encrypt(nonce, source.read_bytes(), associated_data)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(nonce + encrypted)

    def decrypt_file(
        self,
        source: Path,
        destination: Path,
        *,
        associated_data: bytes | None = None,
    ) -> None:
        payload = source.read_bytes()
        if len(payload) < 13:
            raise ValueError("encrypted file is truncated")
        plaintext = self._cipher.decrypt(payload[:12], payload[12:], associated_data)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(plaintext)
