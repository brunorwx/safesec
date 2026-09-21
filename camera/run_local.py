"""Command-line entry point for local camera detection."""

import argparse
import base64
import binascii
import logging
import os
import threading
from collections.abc import Sequence
from pathlib import Path

from apps.web.live import LiveDashboardState
from apps.web.server import DashboardServer
from camera.capture import CameraConfig, OpenCVCamera, VideoFileSource
from camera.runner import FrameSource, PipelineUpdate, run_pipeline
from detection.inference import UltralyticsDetector
from detection.tracking import CentroidTracker
from detection.visualization import annotate_frame
from gateway.authentication import ApiKeyAuthenticator
from storage.encryption import EncryptedFileStore
from storage.retention import RetentionPolicy
from storage.segments import RecordingCatalog, VideoSegmentRecorder

logger = logging.getLogger("safesec.local")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local SafeSec person detection")
    parser.add_argument("--video", help="replay a video file instead of opening a live camera")
    parser.add_argument("--camera", type=int, default=0, help="camera device index")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--weights", default="yolo11n.pt")
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument(
        "--labels",
        default="person,dog",
        help="comma-separated labels to keep (default: person,dog)",
    )
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--preview", action="store_true", help="show an OpenCV preview window")
    parser.add_argument("--dashboard", action="store_true", help="serve the live browser dashboard")
    parser.add_argument("--dashboard-host", default="127.0.0.1")
    parser.add_argument("--dashboard-port", type=int, default=8765)
    parser.add_argument(
        "--dashboard-token",
        default=os.getenv("SAFESEC_DASHBOARD_TOKEN"),
        help="protect the dashboard with Basic/Bearer authentication",
    )
    parser.add_argument("--record", action="store_true", help="save local MP4 recording segments")
    parser.add_argument("--recordings", default="recordings", help="local recording directory")
    parser.add_argument("--max-recordings", type=int, default=100)
    parser.add_argument(
        "--recording-key",
        default=os.getenv("SAFESEC_RECORDING_KEY"),
        help="base64-encoded 32-byte key for encrypted recordings",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    options = build_parser().parse_args(arguments)
    if options.video:
        camera: FrameSource = VideoFileSource(options.video, fps=options.fps)
    else:
        camera = OpenCVCamera(
            CameraConfig(
                device_index=options.camera,
                width=options.width,
                height=options.height,
                fps=options.fps,
            )
        )
    labels = frozenset(
        label.strip().lower() for label in options.labels.split(",") if label.strip()
    )
    if not labels:
        raise ValueError("--labels must contain at least one label")
    detector = UltralyticsDetector(
        confidence_threshold=options.confidence,
        weights=options.weights,
        allowed_labels=labels,
    )
    tracker = CentroidTracker()
    recording_encryption = None
    if options.recording_key:
        try:
            key = base64.b64decode(options.recording_key, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("--recording-key must be valid base64") from error
        recording_encryption = EncryptedFileStore(key)
    retention = RetentionPolicy(max_segments=options.max_recordings)
    recording_root = Path(options.recordings)
    recorder = (
        VideoSegmentRecorder(
            recording_root,
            camera_id="video" if options.video else f"camera:{options.camera}",
            fps=options.fps,
            encryption=recording_encryption,
            retention=retention,
        )
        if options.record
        else None
    )
    dashboard_state = LiveDashboardState() if options.dashboard else None
    if (
        options.dashboard_host not in {"127.0.0.1", "localhost", "::1"}
        and not options.dashboard_token
    ):
        raise ValueError(
            "--dashboard-token is required when binding the dashboard beyond localhost"
        )
    dashboard_authenticator = None
    if options.dashboard_token:
        dashboard_authenticator = ApiKeyAuthenticator()
        dashboard_authenticator.register(
            "dashboard",
            options.dashboard_token,
            {"dashboard:read"},
        )
    dashboard_server = None
    dashboard_thread = None
    if dashboard_state is not None:
        dashboard_server = DashboardServer(
            options.dashboard_host,
            options.dashboard_port,
            dashboard_state.snapshot,
            live_state=dashboard_state,
            authenticator=dashboard_authenticator,
            recording_catalog=RecordingCatalog(recording_root, encryption=recording_encryption),
        )
        dashboard_thread = threading.Thread(
            target=dashboard_server.serve_forever,
            name="safesec-dashboard",
            daemon=True,
        )
        dashboard_thread.start()
        logger.info("dashboard=http://127.0.0.1:%d", dashboard_server.server.server_port)

    def report(update: PipelineUpdate) -> None:
        if recorder is not None:
            recorder.append(update.frame)
        if dashboard_state is not None:
            dashboard_state.update(update)
        visible_tracks = [track for track in update.tracks if track.missed_frames == 0]
        logger.info(
            "frame=%d detections=%d active_tracks=%d",
            update.frame.sequence,
            len(visible_tracks),
            len(update.tracks),
        )
        if options.preview:
            import cv2

            cv2.imshow("SafeSec", annotate_frame(update.frame.image, update.detections))
            if cv2.waitKey(1) & 0xFF == ord("q"):
                raise KeyboardInterrupt

    try:
        processed = run_pipeline(
            camera,
            detector,
            tracker,
            max_frames=options.max_frames,
            on_update=report,
        )
    except KeyboardInterrupt:
        logger.info("stopped by user")
        processed = 0
    finally:
        if options.preview:
            import cv2

            cv2.destroyAllWindows()
        if dashboard_server is not None:
            dashboard_server.close()
        if dashboard_thread is not None:
            dashboard_thread.join(timeout=2)
        if recorder is not None:
            recorder.close()
    logger.info("processed_frames=%d", processed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
