"""OpenCV camera source with an injectable backend for testing."""

from time import monotonic
from typing import Any, Protocol

from .models import CameraConfig, Frame


class CaptureBackend(Protocol):
    def isOpened(self) -> bool: ...
    def set(self, property_id: int, value: float) -> bool: ...
    def read(self) -> tuple[bool, Any]: ...
    def release(self) -> None: ...


class CameraReadError(RuntimeError):
    """Raised when a camera cannot be opened or repeatedly fails to read."""


class OpenCVCamera:
    """Capture BGR frames from a local OpenCV-compatible camera."""

    def __init__(
        self,
        config: CameraConfig | None = None,
        *,
        camera_id: str | None = None,
        backend_factory: Any | None = None,
    ) -> None:
        self.config = config or CameraConfig()
        self.camera_id = camera_id or f"opencv:{self.config.device_index}"
        self._backend_factory = backend_factory or self._default_backend_factory
        self._capture: CaptureBackend | None = None
        self._sequence = 0
        self._failures = 0

    @staticmethod
    def _default_backend_factory(device_index: int) -> CaptureBackend:
        import cv2

        return cv2.VideoCapture(device_index)

    def open(self) -> None:
        if self._capture is not None:
            return
        capture = self._backend_factory(self.config.device_index)
        if not capture.isOpened():
            capture.release()
            raise CameraReadError(f"unable to open camera {self.camera_id}")
        import cv2

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        capture.set(cv2.CAP_PROP_FPS, self.config.fps)
        self._capture = capture

    def read(self) -> Frame:
        if self._capture is None:
            self.open()
        assert self._capture is not None
        success, image = self._capture.read()
        if not success or image is None:
            self._failures += 1
            if self._failures >= self.config.max_consecutive_failures:
                raise CameraReadError(f"camera {self.camera_id} exceeded read failure limit")
            raise CameraReadError(f"camera {self.camera_id} returned no frame")
        self._failures = 0
        frame = Frame.from_image(
            image,
            camera_id=self.camera_id,
            sequence=self._sequence,
            monotonic_time=monotonic(),
        )
        self._sequence += 1
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> "OpenCVCamera":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
