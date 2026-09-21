from detection.models import BoundingBox, Detection
from detection.tracking import CentroidTracker


def detection(sequence: int, left: float, label: str = "person") -> Detection:
    return Detection(
        label=label,
        confidence=0.9,
        box=BoundingBox(left, 10, left + 20, 40),
        frame_sequence=sequence,
        camera_id="cam-1",
        model_name="fake",
        model_version="test",
    )


def test_tracker_keeps_id_for_overlapping_detection() -> None:
    tracker = CentroidTracker(iou_threshold=0.2, max_missed_frames=1)

    first = tracker.update([detection(0, 10)])
    second = tracker.update([detection(1, 12)])

    assert first[0].track_id == second[0].track_id
    assert second[0].missed_frames == 0


def test_tracker_expires_after_missed_frame_limit() -> None:
    tracker = CentroidTracker(max_missed_frames=1)
    first = tracker.update([detection(0, 10)])
    tracker.update([])
    retained = tracker.tracks
    tracker.update([])

    assert retained[0].track_id == first[0].track_id
    assert tracker.tracks == ()


def test_tracker_does_not_match_different_labels() -> None:
    tracker = CentroidTracker()
    first = tracker.update([detection(0, 10, "person")])
    second = tracker.update([detection(1, 10, "vehicle")])

    assert second[0].track_id != first[0].track_id
