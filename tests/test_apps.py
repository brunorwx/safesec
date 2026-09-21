from datetime import UTC, datetime

from alerts.rules import Alert
from apps.web.dashboard import DashboardSnapshot
from detection.models import BoundingBox
from detection.tracking import Track
from gateway.device_api import DeviceStatus


def test_dashboard_payload_is_transport_neutral() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    alert = Alert("person", "cam-1", 1, "Person detected on cam-1", now)
    snapshot = DashboardSnapshot(
        device=DeviceStatus("device-1", True, 1, now),
        tracks=(Track(1, "person", BoundingBox(1, 1, 10, 10), 0.9, 3),),
        recent_alerts=(alert,),
        generated_at=now,
    )

    payload = snapshot.as_payload()
    assert payload["device"]["online"] is True  # type: ignore[index]
    assert payload["tracks"][0]["label"] == "person"  # type: ignore[index]
