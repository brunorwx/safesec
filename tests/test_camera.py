from datetime import UTC

import pytest

from camera.capture import CameraConfig, CameraReadError, Frame, OpenCVCamera


class FakeCapture:
    def __init__(self, opened: bool = True, frames: list[object] | None = None) -> None:
        self.opened = opened
        self.frames = iter(frames or [])
        self.released = False
        self.settings: list[tuple[int, float]] = []

    def isOpened(self) -> bool:
        return self.opened

    def set(self, property_id: int, value: float) -> bool:
        self.settings.append((property_id, value))
        return True

    def read(self) -> tuple[bool, object]:
        try:
            return True, next(self.frames)
        except StopIteration:
            return False, None

    def release(self) -> None:
        self.released = True


class FakeImage:
    shape = (480, 640, 3)


def test_frame_from_image_records_dimensions_and_timezone() -> None:
    frame = Frame.from_image(FakeImage(), camera_id="cam-1", sequence=2, monotonic_time=1.5)

    assert (frame.width, frame.height) == (640, 480)
    assert frame.captured_at.tzinfo == UTC


def test_camera_reads_frames_and_releases_backend() -> None:
    backend = FakeCapture(frames=[FakeImage()])
    camera = OpenCVCamera(backend_factory=lambda _: backend)

    with camera as opened:
        frame = opened.read()

    assert frame.camera_id == "opencv:0"
    assert frame.sequence == 0
    assert backend.released is True


def test_camera_raises_after_consecutive_failures() -> None:
    backend = FakeCapture()
    camera = OpenCVCamera(
        CameraConfig(max_consecutive_failures=2),
        backend_factory=lambda _: backend,
    )

    with pytest.raises(CameraReadError):
        camera.read()
    with pytest.raises(CameraReadError, match="failure limit"):
        camera.read()


def test_camera_rejects_unopened_backend() -> None:
    backend = FakeCapture(opened=False)
    camera = OpenCVCamera(backend_factory=lambda _: backend)

    with pytest.raises(CameraReadError, match="unable to open"):
        camera.open()

    assert backend.released is True
