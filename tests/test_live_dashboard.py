from datetime import UTC, datetime

import numpy as np

from apps.web.live import LiveDashboardState
from camera.capture.models import Frame
from camera.runner import PipelineUpdate
from detection.models import BoundingBox, Detection
from detection.tracking import CentroidTracker


def test_live_dashboard_publishes_frame_and_review_event() -> None:
    captured_at = datetime(2026, 1, 1, tzinfo=UTC)
    frame = Frame.from_image(
        np.zeros((32, 48, 3), dtype=np.uint8),
        camera_id="cam-1",
        sequence=7,
        monotonic_time=1.0,
        captured_at=captured_at,
    )
    detection = Detection(
        "dog",
        0.91,
        BoundingBox(2, 2, 20, 20),
        7,
        "cam-1",
        "fake",
        "test",
    )
    tracks = CentroidTracker().update([detection])
    state = LiveDashboardState(camera_id="cam-1")

    state.update(PipelineUpdate(frame, (detection,), tracks))

    events = state.events_payload()
    assert events[0]["label"] == "dog"
    assert events[0]["occurred_at"] == captured_at.isoformat()
    assert state.event_snapshot(1)
    assert state.wait_for_frame(-1) is not None
