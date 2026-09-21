from camera.capture.models import Frame
from camera.runner import PipelineUpdate, run_pipeline
from detection.models import BoundingBox, Detection
from detection.tracking import CentroidTracker


class FakeImage:
    shape = (100, 100, 3)


class FakeSource:
    def __init__(self) -> None:
        self.closed = False
        self.sequence = 0

    def read(self) -> Frame:
        frame = Frame.from_image(
            FakeImage(),
            camera_id="cam-1",
            sequence=self.sequence,
            monotonic_time=float(self.sequence),
        )
        self.sequence += 1
        return frame

    def close(self) -> None:
        self.closed = True


class FakeDetector:
    def detect(self, frame: Frame) -> list[Detection]:
        return [
            Detection(
                label="person",
                confidence=0.9,
                box=BoundingBox(10, 10, 40, 60),
                frame_sequence=frame.sequence,
                camera_id=frame.camera_id,
                model_name="fake",
                model_version="test",
            )
        ]


def test_pipeline_honors_frame_limit_and_closes_source() -> None:
    source = FakeSource()
    updates: list[PipelineUpdate] = []

    processed = run_pipeline(
        source,
        FakeDetector(),
        CentroidTracker(),
        max_frames=3,
        on_update=updates.append,
    )

    assert processed == 3
    assert len(updates) == 3
    assert updates[-1].tracks[0].track_id == 1
    assert source.closed is True


def test_pipeline_closes_source_when_detector_fails() -> None:
    source = FakeSource()

    class BrokenDetector:
        def detect(self, frame: Frame) -> list[Detection]:
            raise RuntimeError("test failure")

    try:
        run_pipeline(source, BrokenDetector(), CentroidTracker(), max_frames=1)
    except RuntimeError as error:
        assert str(error) == "test failure"
    else:
        raise AssertionError("expected detector failure")

    assert source.closed is True
