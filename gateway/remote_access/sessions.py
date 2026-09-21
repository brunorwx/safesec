"""Opt-in remote sessions with expiry and revocation."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from gateway.authentication import ApiKeyAuthenticator, Principal


@dataclass(frozen=True, slots=True)
class RemoteSession:
    session_id: str
    subject: str
    expires_at: datetime


class RemoteAccessManager:
    def __init__(self, authenticator: ApiKeyAuthenticator) -> None:
        self.authenticator = authenticator
        self.enabled = False
        self._sessions: dict[str, RemoteSession] = {}

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self._sessions.clear()

    def create_session(
        self,
        principal: Principal | None,
        *,
        lifetime: timedelta = timedelta(minutes=15),
        now: datetime | None = None,
    ) -> RemoteSession:
        if not self.enabled:
            raise PermissionError("remote access is disabled")
        if not self.authenticator.authorize(principal, "remote:connect"):
            raise PermissionError("remote:connect scope required")
        assert principal is not None
        if lifetime.total_seconds() <= 0:
            raise ValueError("session lifetime must be positive")
        expires_at = (now or datetime.now(UTC)).astimezone(UTC) + lifetime
        session = RemoteSession(secrets.token_urlsafe(24), principal.subject, expires_at)
        self._sessions[session.session_id] = session
        return session

    def is_valid(self, session_id: str, *, now: datetime | None = None) -> bool:
        session = self._sessions.get(session_id)
        if not self.enabled or session is None:
            return False
        return (now or datetime.now(UTC)).astimezone(UTC) < session.expires_at

    def revoke(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
