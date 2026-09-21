from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from storage.encryption import EncryptedFileStore
from storage.retention import RetentionPolicy
from storage.segments import SegmentRecorder


def timestamp(seconds: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=seconds)


def test_recorder_rotates_by_duration_and_writes_metadata(tmp_path: Path) -> None:
    recorder = SegmentRecorder(tmp_path, camera_id="cam-1", max_duration_seconds=5, max_bytes=100)

    recorder.append(b"one", timestamp(0))
    first = recorder.append(b"two", timestamp(6))
    final = recorder.close()

    assert first is not None
    assert final is not None
    assert Path(first.media_path).read_bytes() == b"one"
    assert Path(final.media_path).read_bytes() == b"two"
    assert Path(first.metadata_path).exists()
    assert not list(tmp_path.glob(".segment-*.tmp"))


def test_recorder_rejects_naive_timestamps(tmp_path: Path) -> None:
    recorder = SegmentRecorder(tmp_path, camera_id="cam-1")

    with pytest.raises(ValueError, match="timezone-aware"):
        recorder.append(b"data", datetime.now())


def test_retention_removes_oldest_segments(tmp_path: Path) -> None:
    recorder = SegmentRecorder(tmp_path, camera_id="cam-1", max_duration_seconds=1)
    recorder.append(b"one", timestamp(0))
    recorder.finalize(timestamp(0))
    recorder.append(b"two", timestamp(2))
    recorder.finalize(timestamp(2))

    removed = RetentionPolicy(max_segments=1).apply(tmp_path)

    assert len(removed) == 1
    assert len(list(tmp_path.glob("*.json"))) == 1
    assert len(list(tmp_path.glob("*.bin"))) == 1


def test_encrypted_store_round_trips_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    encrypted = tmp_path / "encrypted.bin"
    restored = tmp_path / "restored.bin"
    source.write_bytes(b"private recording")
    store = EncryptedFileStore(b"k" * 32)

    store.encrypt_file(source, encrypted, associated_data=b"cam-1")
    store.decrypt_file(encrypted, restored, associated_data=b"cam-1")

    assert restored.read_bytes() == source.read_bytes()
    with pytest.raises(InvalidTag):
        store.decrypt_file(encrypted, tmp_path / "wrong.bin", associated_data=b"other-camera")
