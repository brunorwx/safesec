"""Transport-neutral dashboard read models."""

from dataclasses import dataclass
from datetime import datetime

from alerts.rules import Alert
from detection.tracking import Track
from gateway.device_api import DeviceStatus


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    device: DeviceStatus
    tracks: tuple[Track, ...]
    recent_alerts: tuple[Alert, ...]
    generated_at: datetime

    def as_payload(self) -> dict[str, object]:
        return {
            "device": {
                "id": self.device.device_id,
                "online": self.device.online,
                "camera_count": self.device.camera_count,
                "last_seen": self.device.last_seen.isoformat(),
            },
            "tracks": [
                {
                    "id": track.track_id,
                    "label": track.label,
                    "confidence": track.confidence,
                    "missed_frames": track.missed_frames,
                }
                for track in self.tracks
            ],
            "alerts": [
                {
                    "rule_id": alert.rule_id,
                    "camera_id": alert.camera_id,
                    "track_id": alert.track_id,
                    "message": alert.message,
                    "occurred_at": alert.occurred_at.isoformat(),
                }
                for alert in self.recent_alerts
            ],
            "generated_at": self.generated_at.isoformat(),
        }
