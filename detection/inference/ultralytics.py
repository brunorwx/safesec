"""Lazy Ultralytics adapter; vendor-specific output handling stays here."""

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

from camera.capture.models import Frame
from detection.models import BoundingBox, Detection


class ModelLoadError(RuntimeError):
    """Raised when the configured model cannot be loaded."""


class InferenceError(RuntimeError):
    """Raised when a model fails during inference."""


class UltralyticsDetector:
    def __init__(
        self,
        weights: str = "yolo11n.pt",
        *,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        allowed_labels: frozenset[str] | None = frozenset({"person", "dog", "cat"}),
        model_factory: Callable[[str], Any] | None = None,
        model_name: str = "ultralytics-yolo",
        model_version: str = "unknown",
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1")
        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0 and 1")
        if allowed_labels is not None and not allowed_labels:
            raise ValueError("allowed_labels must not be empty; use None to allow all classes")
        self.weights = str(Path(weights).expanduser())
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.allowed_labels = allowed_labels
        self._model_factory = model_factory
        self.model_name = model_name
        self.model_version = model_version
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        factory = self._model_factory
        if factory is None:
            try:
                from ultralytics import YOLO  # type: ignore[attr-defined]
            except ImportError as error:
                raise ModelLoadError(
                    "install the 'ml' extra to use Ultralytics detection"
                ) from error
            factory = YOLO
        try:
            self._model = factory(self.weights)
        except Exception as error:
            raise ModelLoadError(f"unable to load model weights: {self.weights}") from error
        return self._model

    def detect(self, frame: Frame) -> Sequence[Detection]:
        try:
            model = self._load_model()
            class_ids = self._allowed_class_ids(model)
            inference_options: dict[str, Any] = {
                "conf": self.confidence_threshold,
                "iou": self.iou_threshold,
                "verbose": False,
            }
            if class_ids is not None:
                inference_options["classes"] = class_ids
            results = model(
                frame.image,
                **inference_options,
            )
            return self._convert_results(results, frame)
        except (ModelLoadError, InferenceError):
            raise
        except Exception as error:
            raise InferenceError(f"inference failed for frame {frame.sequence}") from error

    def _convert_results(self, results: Sequence[Any], frame: Frame) -> list[Detection]:
        detections: list[Detection] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            names = getattr(result, "names", {})
            if boxes is None:
                continue
            for box, confidence, class_id in zip(boxes.xyxy, boxes.conf, boxes.cls, strict=True):
                score = float(confidence)
                if score < self.confidence_threshold:
                    continue
                coordinates = [float(value) for value in box]
                label = str(names.get(int(class_id), int(class_id)))
                if self.allowed_labels is not None and label.lower() not in self.allowed_labels:
                    continue
                detections.append(
                    Detection(
                        label=label,
                        confidence=score,
                        box=BoundingBox(*coordinates),
                        frame_sequence=frame.sequence,
                        camera_id=frame.camera_id,
                        model_name=self.model_name,
                        model_version=self.model_version,
                    )
                )
        return detections

    def _allowed_class_ids(self, model: Any) -> list[int] | None:
        if self.allowed_labels is None:
            return None
        names = getattr(model, "names", None)
        if isinstance(names, dict):
            typed_mapping = cast(dict[int, object], names)
            return [
                int(class_id)
                for class_id, label in typed_mapping.items()
                if str(label).lower() in self.allowed_labels
            ]
        if isinstance(names, list):
            typed_list = cast(list[object], names)
            return [
                class_id
                for class_id, label in enumerate(typed_list)
                if str(label).lower() in self.allowed_labels
            ]
        return None
