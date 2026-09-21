"""Camera capture contracts and implementations."""

from .models import CameraConfig, Frame
from .opencv import CameraReadError, OpenCVCamera
from .video import VideoEndOfStream, VideoFileSource

__all__ = [
    "CameraConfig",
    "CameraReadError",
    "Frame",
    "OpenCVCamera",
    "VideoEndOfStream",
    "VideoFileSource",
]
