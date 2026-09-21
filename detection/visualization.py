"""Render human-readable detection labels on camera frames."""

from collections.abc import Sequence
from typing import Any

from .models import Detection


def annotate_frame(image: Any, detections: Sequence[Detection]) -> Any:
    """Return a copy of an image with object names and confidence overlays."""
    import cv2

    annotated = image.copy()
    for detection in detections:
        box = detection.box
        top_left = (round(box.left), round(box.top))
        bottom_right = (round(box.right), round(box.bottom))
        label = f"{detection.label} {detection.confidence:.0%}"
        cv2.rectangle(annotated, top_left, bottom_right, (40, 210, 110), 3)
        label_origin = (top_left[0], max(24, top_left[1] - 8))
        cv2.putText(
            annotated,
            label,
            label_origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (40, 210, 110),
            2,
            cv2.LINE_AA,
        )
    return annotated
