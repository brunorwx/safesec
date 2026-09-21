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
        encrypted = self.encrypt_bytes(source.read_bytes(), associated_data=associated_data)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(encrypted)

    def decrypt_file(
        self,
        source: Path,
        destination: Path,
        *,
        associated_data: bytes | None = None,
    ) -> None:
        plaintext = self.decrypt_bytes(source.read_bytes(), associated_data=associated_data)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(plaintext)

    def encrypt_bytes(self, plaintext: bytes, *, associated_data: bytes | None = None) -> bytes:
        nonce = os.urandom(12)
        return nonce + self._cipher.encrypt(nonce, plaintext, associated_data)

    def decrypt_bytes(self, payload: bytes, *, associated_data: bytes | None = None) -> bytes:
        if len(payload) < 13:
            raise ValueError("encrypted file is truncated")
        return self._cipher.decrypt(payload[:12], payload[12:], associated_data)
