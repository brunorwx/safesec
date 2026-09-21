import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from storage.encryption import EncryptedFileStore
from storage.retention import RetentionPolicy


def test_retention_removes_oldest_segments(tmp_path: Path) -> None:
    for index in range(2):
        media_path = tmp_path / f"segment-{index}.mp4"
        metadata_path = tmp_path / f"segment-{index}.json"
        media_path.write_bytes(f"segment-{index}".encode())
        metadata_path.write_text(
            json.dumps(
                {
                    "segment_id": f"segment-{index}",
                    "media_path": str(media_path),
                    "ended_at": (
                        datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index)
                    ).isoformat(),
                }
            ),
            encoding="utf-8",
        )
    removed = RetentionPolicy(max_segments=1).apply(tmp_path)

    assert removed == ["segment-0"]
    assert not (tmp_path / "segment-0.mp4").exists()
    assert (tmp_path / "segment-1.mp4").exists()


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
