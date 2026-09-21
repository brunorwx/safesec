"""Notification delivery with local cooldown deduplication."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from alerts.rules import Alert


@dataclass(frozen=True, slots=True)
class Notification:
    alert: Alert
    delivered_at: datetime


class NotificationSink(Protocol):
    def send(self, notification: Notification) -> None: ...


class AlertService:
    def __init__(
        self,
        sinks: list[NotificationSink],
        *,
        cooldown: timedelta = timedelta(minutes=1),
    ) -> None:
        if cooldown.total_seconds() < 0:
            raise ValueError("cooldown must not be negative")
        self.sinks = sinks
        self.cooldown = cooldown
        self._last_sent: dict[tuple[str, str, int], datetime] = {}

    def deliver(self, alert: Alert, *, now: datetime | None = None) -> bool:
        delivered_at = (now or datetime.now(UTC)).astimezone(UTC)
        key = (alert.rule_id, alert.camera_id, alert.track_id)
        last_sent = self._last_sent.get(key)
        if last_sent is not None and delivered_at - last_sent < self.cooldown:
            return False
        notification = Notification(alert=alert, delivered_at=delivered_at)
        for sink in self.sinks:
            sink.send(notification)
        self._last_sent[key] = delivered_at
        return True
