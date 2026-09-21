from datetime import UTC
from pathlib import Path

import pytest

from camera.capture import VideoEndOfStream, VideoFileSource
from camera.runner import run_pipeline
from detection.models import BoundingBox, Detection
from detection.tracking import CentroidTracker


class FakeImage:
    shape = (48, 64, 3)


class FakeVideo:
    def __init__(self) -> None:
        self.frames = iter([FakeImage(), FakeImage()])
        self.released = False

    def isOpened(self) -> bool:
        return True

    def set(self, property_id: int, value: float) -> bool:
        return True

    def read(self) -> tuple[bool, object]:
        try:
            return True, next(self.frames)
        except StopIteration:
            return False, None

    def release(self) -> None:
        self.released = True


def test_video_source_replays_frames_with_video_timestamps(tmp_path: Path) -> None:
    backend = FakeVideo()
    source = VideoFileSource(
        tmp_path / "sample.mp4",
        fps=10,
        backend_factory=lambda _: backend,
    )

    first = source.read()
    second = source.read()
    with pytest.raises(VideoEndOfStream):
        source.read()
    source.close()

    assert first.camera_id == "video:sample.mp4"
    assert first.captured_at.tzinfo == UTC
    assert (second.captured_at - first.captured_at).total_seconds() == 0.1
    assert backend.released


def test_pipeline_stops_cleanly_at_video_end(tmp_path: Path) -> None:
    backend = FakeVideo()
    source = VideoFileSource(tmp_path / "sample.mp4", backend_factory=lambda _: backend)

    class Detector:
        def detect(self, frame):
            return [
                Detection(
                    "person",
                    0.9,
                    BoundingBox(1, 1, 10, 10),
                    frame.sequence,
                    frame.camera_id,
                    "fake",
                    "test",
                )
            ]

    processed = run_pipeline(source, Detector(), CentroidTracker())

    assert processed == 2
    assert backend.released
