"""Person presence and zone alert rules."""

from dataclasses import dataclass
from datetime import UTC, datetime

from .events import TrackEvent
from .schedule import Schedule


@dataclass(frozen=True, slots=True)
class Alert:
    rule_id: str
    camera_id: str
    track_id: int
    message: str
    occurred_at: datetime


class PersonPresenceRule:
    def __init__(
        self,
        rule_id: str,
        *,
        minimum_confidence: float = 0.5,
        zone: tuple[float, float, float, float] | None = None,
        schedule: Schedule | None = None,
    ) -> None:
        if not rule_id:
            raise ValueError("rule_id is required")
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        if zone is not None and (zone[2] <= zone[0] or zone[3] <= zone[1]):
            raise ValueError("zone must have positive dimensions")
        self.rule_id = rule_id
        self.minimum_confidence = minimum_confidence
        self.zone = zone
        self.schedule = schedule

    def evaluate(self, event: TrackEvent) -> Alert | None:
        if event.event_type != "started" or event.label != "person":
            return None
        if event.confidence < self.minimum_confidence:
            return None
        if self.schedule is not None and not self.schedule.allows(event.occurred_at):
            return None
        if self.zone is not None and not self._in_zone(event):
            return None
        return Alert(
            rule_id=self.rule_id,
            camera_id=event.camera_id,
            track_id=event.track_id,
            message=f"Person detected on {event.camera_id}",
            occurred_at=event.occurred_at.astimezone(UTC),
        )

    def _in_zone(self, event: TrackEvent) -> bool:
        assert self.zone is not None
        left, top, right, bottom = self.zone
        center_x, center_y = event.box.center
        return left <= center_x <= right and top <= center_y <= bottom
