"""Retention policy for finalized recording segments."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    max_segments: int | None = None
    max_age: timedelta | None = None

    def __post_init__(self) -> None:
        if self.max_segments is not None and self.max_segments < 1:
            raise ValueError("max_segments must be positive")
        if self.max_age is not None and self.max_age.total_seconds() <= 0:
            raise ValueError("max_age must be positive")
        if self.max_segments is None and self.max_age is None:
            raise ValueError("at least one retention limit is required")

    def apply(self, root: Path, *, now: datetime | None = None) -> list[str]:
        metadata_files = sorted(root.glob("*.json"), key=self._created_at)
        cutoff = (now or datetime.now(UTC)).astimezone(UTC) - self.max_age if self.max_age else None
        keep = metadata_files
        if self.max_segments is not None:
            keep = keep[-self.max_segments :]
        removed: list[str] = []
        for metadata_path in metadata_files:
            metadata = self._read(metadata_path)
            ended_at = datetime.fromisoformat(metadata["ended_at"])
            if metadata_path not in keep or (cutoff is not None and ended_at < cutoff):
                media_path = Path(metadata["media_path"])
                media_path.unlink(missing_ok=True)
                metadata_path.unlink(missing_ok=True)
                removed.append(metadata["segment_id"])
        return removed

    @staticmethod
    def _created_at(path: Path) -> float:
        return path.stat().st_mtime

    @staticmethod
    def _read(path: Path) -> dict[str, str]:
        return cast(dict[str, str], json.loads(path.read_text(encoding="utf-8")))
