from datetime import UTC, datetime, timedelta

import pytest

from gateway.authentication import ApiKeyAuthenticator, AuditLog, RateLimiter
from gateway.device_api import DeviceApi, OfflineQueue


def test_api_key_authentication_and_scope_authorization() -> None:
    authenticator = ApiKeyAuthenticator(iterations=100_000)
    token = authenticator.issue("owner", {"device:read"})

    principal = authenticator.authenticate("owner", token)

    assert principal is not None
    assert authenticator.authorize(principal, "device:read")
    assert not authenticator.authorize(principal, "device:write")
    assert authenticator.authenticate("owner", "wrong") is None


def test_device_status_requires_scope() -> None:
    authenticator = ApiKeyAuthenticator(iterations=100_000)
    token = authenticator.issue("owner", {"device:read"})
    principal = authenticator.authenticate("owner", token)
    api = DeviceApi(authenticator, device_id="device-1")
    api.update_status(online=True, camera_count=1)

    assert principal is not None
    assert api.get_status(principal).online
    with pytest.raises(PermissionError):
        api.get_status(None)


def test_rotation_invalidates_old_token_and_rate_limiter_bounds_requests() -> None:
    authenticator = ApiKeyAuthenticator(iterations=100_000)
    old_token = authenticator.issue("owner", {"device:read"})
    new_token = authenticator.rotate("owner")
    assert authenticator.authenticate("owner", old_token) is None
    assert authenticator.authenticate("owner", new_token) is not None

    limiter = RateLimiter(limit=2, window=timedelta(minutes=1))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert limiter.allow("owner", now=now)
    assert limiter.allow("owner", now=now + timedelta(seconds=1))
    assert not limiter.allow("owner", now=now + timedelta(seconds=2))

    audit = AuditLog()
    audit.record("owner", "device.read", success=True, occurred_at=now)
    assert audit.events[0].action == "device.read"


def test_audit_log_reloads_persisted_events(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    AuditLog(path).record("owner", "device.read", success=True, occurred_at=moment)

    restored = AuditLog(path)

    assert restored.events[0].occurred_at == moment
    assert restored.events[0].success


def test_offline_queue_retries_without_losing_unsent_updates() -> None:
    queue: OfflineQueue[str] = OfflineQueue(max_size=2)
    queue.enqueue("one")
    queue.enqueue("two")
    queue.enqueue("three")
    sent: list[str] = []

    assert queue.flush(lambda payload: sent.append(payload)) == 2
    assert sent == ["two", "three"]

    queue.enqueue("four")

    def unavailable(_: str) -> None:
        raise ConnectionError("offline")

    assert queue.flush(unavailable) == 0
    assert len(queue.pending) == 1
