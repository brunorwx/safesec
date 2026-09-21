"""Atomic, rotating storage for encoded camera segments."""

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, cast
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class SegmentMetadata:
    segment_id: str
    camera_id: str
    started_at: datetime
    ended_at: datetime
    byte_count: int
    media_path: str
    metadata_path: str


class SegmentRecorder:
    """Write encoded chunks to bounded segments with a JSON sidecar."""

    def __init__(
        self,
        root: Path,
        *,
        camera_id: str,
        max_duration_seconds: float = 60.0,
        max_bytes: int = 64 * 1024 * 1024,
        suffix: str = ".bin",
    ) -> None:
        if max_duration_seconds <= 0 or max_bytes <= 0:
            raise ValueError("segment limits must be positive")
        if not camera_id:
            raise ValueError("camera_id is required")
        self.root = root
        self.camera_id = camera_id
        self.max_duration_seconds = max_duration_seconds
        self.max_bytes = max_bytes
        self.suffix = suffix if suffix.startswith(".") else f".{suffix}"
        self._file: BinaryIO | None = None
        self._temp_path: Path | None = None
        self._segment_id: str | None = None
        self._started_at: datetime | None = None
        self._byte_count = 0
        self._last_metadata: SegmentMetadata | None = None

    @property
    def last_metadata(self) -> SegmentMetadata | None:
        return self._last_metadata

    def append(self, encoded_bytes: bytes, captured_at: datetime) -> SegmentMetadata | None:
        if not encoded_bytes:
            raise ValueError("encoded_bytes must not be empty")
        if captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        captured_at = captured_at.astimezone(UTC)
        if self._should_rotate(captured_at, len(encoded_bytes)):
            self.finalize(captured_at)
        if self._file is None:
            self._start(captured_at)
        assert self._file is not None
        self._file.write(encoded_bytes)
        self._file.flush()
        self._byte_count += len(encoded_bytes)
        return self._last_metadata

    def finalize(self, ended_at: datetime | None = None) -> SegmentMetadata | None:
        if self._file is None or self._temp_path is None or self._segment_id is None:
            return None
        assert self._started_at is not None
        end = (ended_at or datetime.now(UTC)).astimezone(UTC)
        self._file.flush()
        self._file.close()
        media_path = self.root / f"{self._segment_id}{self.suffix}"
        metadata_path = self.root / f"{self._segment_id}.json"
        self._temp_path.replace(media_path)
        metadata = SegmentMetadata(
            segment_id=self._segment_id,
            camera_id=self.camera_id,
            started_at=self._started_at,
            ended_at=end,
            byte_count=self._byte_count,
            media_path=str(media_path),
            metadata_path=str(metadata_path),
        )
        metadata_path.write_text(
            json.dumps(asdict(metadata), default=self._json_default, indent=2),
            encoding="utf-8",
        )
        self._last_metadata = metadata
        self._file = None
        self._temp_path = None
        self._segment_id = None
        self._started_at = None
        self._byte_count = 0
        return metadata

    def close(self) -> SegmentMetadata | None:
        return self.finalize()

    def _start(self, started_at: datetime) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._segment_id = f"{started_at.strftime('%Y%m%dT%H%M%S.%fZ')}-{uuid4().hex[:8]}"
        temp_file = tempfile.NamedTemporaryFile(
            dir=self.root,
            prefix=".segment-",
            suffix=".tmp",
            delete=False,
        )
        self._file = cast(BinaryIO, temp_file)
        self._temp_path = Path(temp_file.name)
        self._started_at = started_at
        self._byte_count = 0

    def _should_rotate(self, captured_at: datetime, incoming_bytes: int) -> bool:
        if self._file is None or self._started_at is None:
            return False
        duration = (captured_at - self._started_at).total_seconds()
        return (
            duration >= self.max_duration_seconds
            or self._byte_count + incoming_bytes > self.max_bytes
        )

    @staticmethod
    def _json_default(value: object) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f"unsupported metadata value: {type(value)!r}")
