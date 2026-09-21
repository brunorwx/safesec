"""Mobile-facing notification payloads."""

from dataclasses import dataclass
from datetime import datetime

from alerts.rules import Alert


@dataclass(frozen=True, slots=True)
class MobileAlert:
    title: str
    body: str
    camera_id: str
    occurred_at: datetime

    @classmethod
    def from_alert(cls, alert: Alert) -> "MobileAlert":
        return cls(
            title="SafeSec alert",
            body=alert.message,
            camera_id=alert.camera_id,
            occurred_at=alert.occurred_at,
        )
