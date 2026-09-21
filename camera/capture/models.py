"""Stable camera frame contracts."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class CameraConfig:
    """Configuration for a local camera device."""

    device_index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    max_consecutive_failures: int = 3

    def __post_init__(self) -> None:
        if self.device_index < 0:
            raise ValueError("device_index must be non-negative")
        if self.width <= 0 or self.height <= 0 or self.fps <= 0:
            raise ValueError("width, height, and fps must be positive")
        if self.max_consecutive_failures <= 0:
            raise ValueError("max_consecutive_failures must be positive")


@dataclass(frozen=True, slots=True)
class Frame:
    """A captured BGR image and the metadata needed by downstream stages."""

    image: Any
    camera_id: str
    sequence: int
    captured_at: datetime
    monotonic_time: float
    width: int
    height: int
    pixel_format: str = "bgr24"

    def __post_init__(self) -> None:
        if not self.camera_id:
            raise ValueError("camera_id must not be empty")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("frame dimensions must be positive")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        if self.pixel_format != "bgr24":
            raise ValueError("unsupported pixel format")

    @classmethod
    def from_image(
        cls,
        image: Any,
        *,
        camera_id: str,
        sequence: int,
        monotonic_time: float,
        captured_at: datetime | None = None,
    ) -> "Frame":
        shape: Any = getattr(image, "shape", ())
        if len(shape) < 2:
            raise ValueError("image must expose height and width")
        return cls(
            image=image,
            camera_id=camera_id,
            sequence=sequence,
            captured_at=captured_at or datetime.now(UTC),
            monotonic_time=monotonic_time,
            width=int(shape[1]),
            height=int(shape[0]),
        )
