"""Inference protocol used by pipeline code and test doubles."""

from collections.abc import Sequence
from typing import Any, Protocol

from camera.capture.models import Frame
from detection.models import Detection


class Detector(Protocol):
    def detect(self, frame: Frame) -> Sequence[Detection]: ...


class ModelBackend(Protocol):
    def __call__(self, image: Any, *, conf: float, iou: float, verbose: bool) -> Sequence[Any]: ...
