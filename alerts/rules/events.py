"""Track lifecycle events used by alert rules."""

from dataclasses import dataclass
from datetime import UTC, datetime

from detection.models import BoundingBox
from detection.tracking import Track


@dataclass(frozen=True, slots=True)
class TrackEvent:
    event_type: str
    camera_id: str
    track_id: int
    label: str
    confidence: float
    box: BoundingBox
    occurred_at: datetime

    def __post_init__(self) -> None:
        if self.event_type not in {"started", "ended"}:
            raise ValueError("event_type must be started or ended")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")


class TrackEventBuilder:
    """Turn tracker snapshots into one-shot track start/end events."""

    def __init__(self) -> None:
        self._active: dict[tuple[str, int], Track] = {}

    def observe(
        self,
        camera_id: str,
        tracks: tuple[Track, ...],
        occurred_at: datetime | None = None,
    ) -> tuple[TrackEvent, ...]:
        now = (occurred_at or datetime.now(UTC)).astimezone(UTC)
        current = {
            (camera_id, track.track_id): track for track in tracks if track.missed_frames == 0
        }
        events: list[TrackEvent] = []
        for key, track in current.items():
            if key not in self._active:
                events.append(self._event("started", camera_id, track, now))
        for key, track in self._active.items():
            if key not in current:
                events.append(self._event("ended", camera_id, track, now))
        self._active = current
        return tuple(events)

    @staticmethod
    def _event(event_type: str, camera_id: str, track: Track, occurred_at: datetime) -> TrackEvent:
        return TrackEvent(
            event_type=event_type,
            camera_id=camera_id,
            track_id=track.track_id,
            label=track.label,
            confidence=track.confidence,
            box=track.box,
            occurred_at=occurred_at,
        )
