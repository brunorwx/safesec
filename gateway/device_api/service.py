"""Authenticated device state service."""

from dataclasses import dataclass
from datetime import UTC, datetime

from gateway.authentication import ApiKeyAuthenticator, Principal


@dataclass(frozen=True, slots=True)
class DeviceStatus:
    device_id: str
    online: bool
    camera_count: int
    last_seen: datetime


class DeviceApi:
    def __init__(self, authenticator: ApiKeyAuthenticator, *, device_id: str) -> None:
        self.authenticator = authenticator
        self.device_id = device_id
        self._status = DeviceStatus(device_id, False, 0, datetime.now(UTC))

    def update_status(
        self,
        *,
        online: bool,
        camera_count: int,
        last_seen: datetime | None = None,
    ) -> None:
        if camera_count < 0:
            raise ValueError("camera_count must be non-negative")
        self._status = DeviceStatus(
            self.device_id,
            online,
            camera_count,
            (last_seen or datetime.now(UTC)).astimezone(UTC),
        )

    def get_status(self, principal: Principal | None) -> DeviceStatus:
        if not self.authenticator.authorize(principal, "device:read"):
            raise PermissionError("device:read scope required")
        return self._status
