"""OpenCV video-file source using the same Frame contract as live cameras."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import Any

from .models import Frame
from .opencv import CameraReadError, CaptureBackend


class VideoEndOfStream(CameraReadError, StopIteration):
    """Raised internally when a video file has no more frames."""


class VideoFileSource:
    """Replay a video file as timestamped SafeSec frames."""

    def __init__(
        self,
        path: str | Path,
        *,
        camera_id: str | None = None,
        fps: float = 30.0,
        backend_factory: Any | None = None,
    ) -> None:
        if fps <= 0:
            raise ValueError("fps must be positive")
        self.path = Path(path)
        self.camera_id = camera_id or f"video:{self.path.name}"
        self.fps = fps
        self._backend_factory = backend_factory or self._default_backend_factory
        self._capture: CaptureBackend | None = None
        self._sequence = 0
        self._started_at: datetime | None = None

    @staticmethod
    def _default_backend_factory(path: str) -> CaptureBackend:
        import cv2

        return cv2.VideoCapture(path)

    def open(self) -> None:
        if self._capture is not None:
            return
        capture = self._backend_factory(str(self.path))
        if not capture.isOpened():
            capture.release()
            raise CameraReadError(f"unable to open video file {self.path}")
        self._capture = capture
        self._started_at = datetime.now(UTC)

    def read(self) -> Frame:
        if self._capture is None:
            self.open()
        assert self._capture is not None
        success, image = self._capture.read()
        if not success or image is None:
            raise VideoEndOfStream(f"video file ended: {self.path}")
        assert self._started_at is not None
        captured_at = self._started_at + timedelta(seconds=self._sequence / self.fps)
        frame = Frame.from_image(
            image,
            camera_id=self.camera_id,
            sequence=self._sequence,
            captured_at=captured_at,
            monotonic_time=monotonic(),
        )
        self._sequence += 1
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> "VideoFileSource":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
