"""Local camera-to-detection runner."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from camera.capture.models import Frame
from detection.inference.protocol import Detector
from detection.models import Detection
from detection.tracking import CentroidTracker, Track


class FrameSource(Protocol):
    def read(self) -> Frame: ...
    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class PipelineUpdate:
    frame: Frame
    detections: tuple[Detection, ...]
    tracks: tuple[Track, ...]


def run_pipeline(
    source: FrameSource,
    detector: Detector,
    tracker: CentroidTracker,
    *,
    max_frames: int | None = None,
    on_update: Callable[[PipelineUpdate], None] | None = None,
) -> int:
    """Run the local pipeline and return the number of processed frames."""
    if max_frames is not None and max_frames <= 0:
        raise ValueError("max_frames must be positive when provided")

    processed = 0
    try:
        while max_frames is None or processed < max_frames:
            try:
                frame = source.read()
            except StopIteration:
                break
            detections = tuple(detector.detect(frame))
            tracks = tracker.update(list(detections))
            update = PipelineUpdate(frame=frame, detections=detections, tracks=tracks)
            if on_update is not None:
                on_update(update)
            processed += 1
    finally:
        source.close()
    return processed
