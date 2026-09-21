"""Small deterministic IoU tracker suitable for the first local pipeline."""

from dataclasses import dataclass

from detection.models import BoundingBox, Detection


@dataclass(frozen=True, slots=True)
class Track:
    track_id: int
    label: str
    box: BoundingBox
    confidence: float
    last_frame_sequence: int
    missed_frames: int = 0


class CentroidTracker:
    def __init__(self, *, iou_threshold: float = 0.3, max_missed_frames: int = 5) -> None:
        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0 and 1")
        if max_missed_frames < 0:
            raise ValueError("max_missed_frames must be non-negative")
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames
        self._tracks: dict[int, Track] = {}
        self._next_id = 1

    @property
    def tracks(self) -> tuple[Track, ...]:
        return tuple(self._tracks.values())

    def update(self, detections: list[Detection]) -> tuple[Track, ...]:
        unmatched_tracks = set(self._tracks)
        matched_ids: set[int] = set()
        updated: dict[int, Track] = {}
        for detection in detections:
            candidate_id = self._best_match(detection, unmatched_tracks)
            if candidate_id is None:
                candidate_id = self._next_id
                self._next_id += 1
            else:
                unmatched_tracks.remove(candidate_id)
            matched_ids.add(candidate_id)
            updated[candidate_id] = Track(
                track_id=candidate_id,
                label=detection.label,
                box=detection.box,
                confidence=detection.confidence,
                last_frame_sequence=detection.frame_sequence,
            )
        for track_id in unmatched_tracks:
            previous = self._tracks[track_id]
            missed = previous.missed_frames + 1
            if missed <= self.max_missed_frames:
                updated[track_id] = Track(
                    track_id=previous.track_id,
                    label=previous.label,
                    box=previous.box,
                    confidence=previous.confidence,
                    last_frame_sequence=previous.last_frame_sequence,
                    missed_frames=missed,
                )
        self._tracks = updated
        return self.tracks

    def _best_match(self, detection: Detection, candidates: set[int]) -> int | None:
        eligible = [
            (track_id, self._tracks[track_id].box.iou(detection.box))
            for track_id in candidates
            if self._tracks[track_id].label == detection.label
        ]
        if not eligible:
            return None
        track_id, overlap = max(eligible, key=lambda item: item[1])
        return track_id if overlap >= self.iou_threshold else None
