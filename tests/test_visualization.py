import numpy as np

from detection.models import BoundingBox, Detection
from detection.visualization import annotate_frame


def test_annotation_draws_object_name_and_box() -> None:
    image = np.zeros((80, 120, 3), dtype=np.uint8)
    detection = Detection(
        "dog",
        0.9,
        BoundingBox(10, 20, 60, 70),
        0,
        "camera-1",
        "fake",
        "test",
    )

    annotated = annotate_frame(image, [detection])

    assert annotated.shape == image.shape
    assert int(annotated.sum()) > 0
    assert int(image.sum()) == 0
