"""Salted API-key authentication for local device access."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    scopes: frozenset[str]


@dataclass(frozen=True, slots=True)
class _Credential:
    salt: bytes
    digest: bytes
    principal: Principal


class ApiKeyAuthenticator:
    def __init__(self, *, iterations: int = 600_000) -> None:
        if iterations < 100_000:
            raise ValueError("iterations must be at least 100000")
        self.iterations = iterations
        self._credentials: dict[str, _Credential] = {}

    def issue(self, subject: str, scopes: set[str]) -> str:
        if not subject or not scopes:
            raise ValueError("subject and scopes are required")
        token = secrets.token_urlsafe(32)
        self.register(subject, token, scopes)
        return token

    def register(self, subject: str, token: str, scopes: set[str]) -> None:
        """Register a caller-provided token without storing it in plaintext."""
        if not subject or not token or not scopes:
            raise ValueError("subject, token, and scopes are required")
        salt = secrets.token_bytes(16)
        digest = self._digest(token, salt)
        self._credentials[subject] = _Credential(
            salt,
            digest,
            Principal(subject, frozenset(scopes)),
        )

    def authenticate(self, subject: str, token: str) -> Principal | None:
        credential = self._credentials.get(subject)
        if credential is None:
            return None
        candidate = self._digest(token, credential.salt)
        if not hmac.compare_digest(candidate, credential.digest):
            return None
        return credential.principal

    def authorize(self, principal: Principal | None, scope: str) -> bool:
        return principal is not None and scope in principal.scopes

    def revoke(self, subject: str) -> None:
        self._credentials.pop(subject, None)

    def rotate(self, subject: str) -> str:
        credential = self._credentials.get(subject)
        if credential is None:
            raise KeyError(subject)
        return self.issue(subject, set(credential.principal.scopes))

    def _digest(self, token: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", token.encode(), salt, self.iterations)
