from datetime import UTC, datetime, timedelta
from pathlib import Path

from camera.capture.models import Frame
from storage.encryption import EncryptedFileStore
from storage.segments import RecordingCatalog, VideoSegmentRecorder


class FakeImage:
    shape = (24, 32, 3)


class FakeWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.frames = 0
        self.path.write_bytes(b"mp4")

    def write(self, image: object) -> None:
        self.frames += 1

    def release(self) -> None:
        self.path.write_bytes(f"frames={self.frames}".encode())


def make_frame(sequence: int, captured_at: datetime) -> Frame:
    return Frame.from_image(
        FakeImage(),
        camera_id="camera-1",
        sequence=sequence,
        captured_at=captured_at,
        monotonic_time=float(sequence),
    )


def test_video_recorder_rotates_and_publishes_metadata(tmp_path: Path) -> None:
    writers: list[FakeWriter] = []

    def factory(path: Path, fps: float, size: tuple[int, int]) -> FakeWriter:
        writer = FakeWriter(path)
        writers.append(writer)
        return writer

    recorder = VideoSegmentRecorder(
        tmp_path,
        camera_id="camera-1",
        max_duration_seconds=1,
        writer_factory=factory,
    )
    start = datetime(2026, 1, 1, tzinfo=UTC)

    recorder.append(make_frame(0, start))
    recorder.append(make_frame(1, start + timedelta(seconds=2)))
    recorder.close()

    assert len(writers) == 2
    assert len(list(tmp_path.glob("*.mp4"))) == 2
    assert len(list(tmp_path.glob("*.json"))) == 2
    assert not list(tmp_path.glob("*.tmp.mp4"))


def test_encrypted_recording_catalog_decrypts_playback_bytes(tmp_path: Path) -> None:
    def factory(path: Path, fps: float, size: tuple[int, int]) -> FakeWriter:
        return FakeWriter(path)

    recorder = VideoSegmentRecorder(
        tmp_path,
        camera_id="camera-1",
        encryption=EncryptedFileStore(b"k" * 32),
        writer_factory=factory,
    )
    recorder.append(make_frame(0, datetime(2026, 1, 1, tzinfo=UTC)))
    metadata = recorder.close()

    assert metadata is not None
    assert metadata.encrypted
    assert metadata.media_path.endswith(".mp4.enc")
    catalog = RecordingCatalog(tmp_path, encryption=EncryptedFileStore(b"k" * 32))
    playback = catalog.read_media(metadata.segment_id)

    assert playback is not None
    assert playback[1] == b"frames=1"
