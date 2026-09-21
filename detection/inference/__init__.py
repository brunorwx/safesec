"""Inference adapters."""

from .protocol import Detector
from .ultralytics import UltralyticsDetector

__all__ = ["Detector", "UltralyticsDetector"]
