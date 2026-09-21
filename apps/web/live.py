"""Thread-safe live frame and detection state for the local dashboard."""

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from alerts.rules import Alert
from camera.runner import PipelineUpdate
from detection.tracking import Track
from detection.visualization import annotate_frame
from gateway.device_api import DeviceStatus

from .dashboard import DashboardSnapshot


@dataclass(frozen=True, slots=True)
class DashboardEvent:
    event_id: int
    alert: Alert
    label: str
    confidence: float
    snapshot: bytes


class LiveDashboardState:
    """Publish the newest frame and track-start events to dashboard clients."""

    def __init__(self, *, device_id: str = "local-device", camera_id: str = "camera-0") -> None:
        self.device_id = device_id
        self.camera_id = camera_id
        self._condition = threading.Condition()
        self._latest_frame: bytes | None = None
        self._frame_sequence = -1
        self._tracks: tuple[Track, ...] = ()
        self._events: list[DashboardEvent] = []
        self._active_track_ids: set[int] = set()
        self._next_event_id = 1
        self._online = False
        self._last_seen = datetime.now(UTC)

    def update(self, update: PipelineUpdate) -> None:
        import cv2

        annotated = annotate_frame(update.frame.image, update.detections)
        success, encoded = cv2.imencode(".jpg", annotated)
        if not success:
            raise RuntimeError("unable to encode dashboard frame")
        frame_bytes = encoded.tobytes()
        visible_tracks = tuple(track for track in update.tracks if track.missed_frames == 0)
        visible_ids = {track.track_id for track in visible_tracks}
        with self._condition:
            for track in visible_tracks:
                if track.track_id not in self._active_track_ids:
                    alert = Alert(
                        rule_id="detection",
                        camera_id=update.frame.camera_id,
                        track_id=track.track_id,
                        message=f"{track.label.title()} detected",
                        occurred_at=update.frame.captured_at,
                    )
                    self._events.append(
                        DashboardEvent(
                            self._next_event_id,
                            alert,
                            track.label,
                            track.confidence,
                            frame_bytes,
                        )
                    )
                    self._next_event_id += 1
            self._active_track_ids = visible_ids
            self._tracks = update.tracks
            self._latest_frame = frame_bytes
            self._frame_sequence = update.frame.sequence
            self._online = True
            self._last_seen = update.frame.captured_at
            self._condition.notify_all()

    def snapshot(self) -> DashboardSnapshot:
        with self._condition:
            status = DeviceStatus(
                self.device_id,
                self._online,
                1,
                self._last_seen,
            )
            return DashboardSnapshot(
                device=status,
                tracks=self._tracks,
                recent_alerts=tuple(event.alert for event in self._events[-50:]),
                generated_at=datetime.now(UTC),
            )

    def events_payload(self) -> list[dict[str, Any]]:
        with self._condition:
            return [
                {
                    "id": event.event_id,
                    "label": event.label,
                    "camera_id": event.alert.camera_id,
                    "track_id": event.alert.track_id,
                    "confidence": event.confidence,
                    "occurred_at": event.alert.occurred_at.isoformat(),
                    "snapshot_url": f"/api/events/{event.event_id}/snapshot",
                }
                for event in reversed(self._events[-100:])
            ]

    def event_snapshot(self, event_id: int) -> bytes | None:
        with self._condition:
            for event in self._events:
                if event.event_id == event_id:
                    return event.snapshot
        return None

    def wait_for_frame(self, after_sequence: int) -> tuple[int, bytes] | None:
        with self._condition:
            self._condition.wait_for(
                lambda: self._latest_frame is not None and self._frame_sequence > after_sequence,
                timeout=2,
            )
            if self._latest_frame is None or self._frame_sequence <= after_sequence:
                return None
            return self._frame_sequence, self._latest_frame
