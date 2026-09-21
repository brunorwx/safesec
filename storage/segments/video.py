"""Local MP4 segment recording for self-hosted camera operation."""

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from camera.capture.models import Frame
from storage.encryption import EncryptedFileStore
from storage.retention import RetentionPolicy


@dataclass(frozen=True, slots=True)
class VideoSegmentMetadata:
    segment_id: str
    camera_id: str
    started_at: datetime
    ended_at: datetime
    frame_count: int
    media_path: str
    metadata_path: str
    encrypted: bool


class VideoSegmentRecorder:
    """Encode frames locally into rotating MP4 files with metadata sidecars."""

    def __init__(
        self,
        root: Path,
        *,
        camera_id: str,
        fps: float = 30.0,
        max_duration_seconds: float = 300.0,
        writer_factory: Callable[[Path, float, tuple[int, int]], Any] | None = None,
        encryption: EncryptedFileStore | None = None,
        retention: RetentionPolicy | None = None,
    ) -> None:
        if not camera_id:
            raise ValueError("camera_id is required")
        if fps <= 0 or max_duration_seconds <= 0:
            raise ValueError("fps and max_duration_seconds must be positive")
        self.root = root
        self.camera_id = camera_id
        self.fps = fps
        self.max_duration_seconds = max_duration_seconds
        self.encryption = encryption
        self.retention = retention
        self._writer_factory = writer_factory or self._default_writer_factory
        self._writer: Any | None = None
        self._temp_path: Path | None = None
        self._segment_id: str | None = None
        self._started_at: datetime | None = None
        self._frame_count = 0
        self._last_metadata: VideoSegmentMetadata | None = None

    @property
    def last_metadata(self) -> VideoSegmentMetadata | None:
        return self._last_metadata

    def append(self, frame: Frame) -> VideoSegmentMetadata | None:
        if self._should_rotate(frame.captured_at):
            self.finalize(frame.captured_at)
        if self._writer is None:
            self._start(frame)
        assert self._writer is not None
        self._writer.write(frame.image)
        self._frame_count += 1
        return self._last_metadata

    def finalize(self, ended_at: datetime | None = None) -> VideoSegmentMetadata | None:
        if self._writer is None or self._temp_path is None or self._segment_id is None:
            return None
        assert self._started_at is not None
        self._writer.release()
        media_path = self.root / f"{self._segment_id}.mp4"
        metadata_path = self.root / f"{self._segment_id}.json"
        if self.encryption is None:
            self._temp_path.replace(media_path)
        else:
            encrypted_path = self.root / f".{self._segment_id}.tmp.mp4.enc"
            self.encryption.encrypt_file(
                self._temp_path,
                encrypted_path,
                associated_data=self._segment_id.encode("utf-8"),
            )
            self._temp_path.unlink(missing_ok=True)
            encrypted_path.replace(self.root / f"{self._segment_id}.mp4.enc")
            media_path = self.root / f"{self._segment_id}.mp4.enc"
        metadata = VideoSegmentMetadata(
            segment_id=self._segment_id,
            camera_id=self.camera_id,
            started_at=self._started_at,
            ended_at=(ended_at or datetime.now(UTC)).astimezone(UTC),
            frame_count=self._frame_count,
            media_path=str(media_path),
            metadata_path=str(metadata_path),
            encrypted=self.encryption is not None,
        )
        metadata_path.write_text(
            json.dumps(asdict(metadata), default=self._json_default, indent=2),
            encoding="utf-8",
        )
        if self.retention is not None:
            self.retention.apply(self.root)
        self._last_metadata = metadata
        self._writer = None
        self._temp_path = None
        self._segment_id = None
        self._started_at = None
        self._frame_count = 0
        return metadata

    def close(self) -> VideoSegmentMetadata | None:
        return self.finalize()

    @staticmethod
    def _default_writer_factory(path: Path, fps: float, size: tuple[int, int]) -> Any:
        import cv2

        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"mp4v"),  # type: ignore[attr-defined]
            fps,
            size,
        )
        if not writer.isOpened():
            writer.release()
            raise RuntimeError(f"unable to open video writer for {path}")
        return writer

    def _start(self, frame: Frame) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._segment_id = f"{frame.captured_at.strftime('%Y%m%dT%H%M%S.%fZ')}-{uuid4().hex[:8]}"
        self._temp_path = self.root / f".{self._segment_id}.tmp.mp4"
        self._writer = self._writer_factory(
            self._temp_path,
            self.fps,
            (frame.width, frame.height),
        )
        self._started_at = frame.captured_at
        self._frame_count = 0

    def _should_rotate(self, captured_at: datetime) -> bool:
        if self._writer is None or self._started_at is None:
            return False
        return (captured_at - self._started_at).total_seconds() >= self.max_duration_seconds

    @staticmethod
    def _json_default(value: object) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f"unsupported metadata value: {type(value)!r}")


class RecordingCatalog:
    """List finalized recordings and read plaintext media for local playback."""

    def __init__(self, root: Path, *, encryption: EncryptedFileStore | None = None) -> None:
        self.root = root
        self.encryption = encryption

    def list_segments(self) -> list[VideoSegmentMetadata]:
        segments: list[VideoSegmentMetadata] = []
        for metadata_path in sorted(self.root.glob("*.json"), reverse=True):
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            segments.append(
                VideoSegmentMetadata(
                    segment_id=payload["segment_id"],
                    camera_id=payload["camera_id"],
                    started_at=datetime.fromisoformat(payload["started_at"]),
                    ended_at=datetime.fromisoformat(payload["ended_at"]),
                    frame_count=int(payload["frame_count"]),
                    media_path=payload["media_path"],
                    metadata_path=payload["metadata_path"],
                    encrypted=bool(payload.get("encrypted", False)),
                )
            )
        return segments

    def list_payload(self) -> list[dict[str, object]]:
        return [
            {
                "id": segment.segment_id,
                "camera_id": segment.camera_id,
                "started_at": segment.started_at.isoformat(),
                "ended_at": segment.ended_at.isoformat(),
                "frame_count": segment.frame_count,
                "encrypted": segment.encrypted,
                "video_url": f"/api/recordings/{segment.segment_id}/video",
            }
            for segment in self.list_segments()
        ]

    def read_media(self, segment_id: str) -> tuple[VideoSegmentMetadata, bytes] | None:
        segment = next(
            (item for item in self.list_segments() if item.segment_id == segment_id),
            None,
        )
        if segment is None:
            return None
        payload = Path(segment.media_path).read_bytes()
        if segment.encrypted:
            if self.encryption is None:
                raise PermissionError("recording encryption key is not configured")
            payload = self.encryption.decrypt_bytes(
                payload,
                associated_data=segment.segment_id.encode("utf-8"),
            )
        return segment, payload
