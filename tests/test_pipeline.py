from camera.capture.models import Frame
from detection.models import BoundingBox, Detection
from detection.tracking import CentroidTracker


class FakeImage:
    shape = (100, 100, 3)


class FakeDetector:
    def detect(self, frame: Frame) -> list[Detection]:
        return [
            Detection(
                label="person",
                confidence=0.95,
                box=BoundingBox(10, 10, 40, 70),
                frame_sequence=frame.sequence,
                camera_id=frame.camera_id,
                model_name="fake",
                model_version="test",
            )
        ]


def test_camera_detection_tracking_contracts_compose() -> None:
    frame = Frame.from_image(FakeImage(), camera_id="cam-1", sequence=0, monotonic_time=1.0)
    detection = FakeDetector().detect(frame)
    tracks = CentroidTracker().update(detection)

    assert tracks[0].label == "person"
    assert tracks[0].last_frame_sequence == frame.sequence
