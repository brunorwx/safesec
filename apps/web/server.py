"""Small local dashboard server for the operational web shell."""

import base64
import json
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from gateway.authentication import ApiKeyAuthenticator

from .dashboard import DashboardSnapshot
from .live import LiveDashboardState


class DashboardServer:
    def __init__(
        self,
        host: str,
        port: int,
        snapshot_provider: Callable[[], DashboardSnapshot],
        live_state: LiveDashboardState | None = None,
        authenticator: ApiKeyAuthenticator | None = None,
        auth_subject: str = "dashboard",
    ) -> None:
        provider = snapshot_provider
        state = live_state
        auth = authenticator

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if not self._authorized():
                    return
                if self.path == "/api/status":
                    self._json_response(provider().as_payload())
                    return
                if self.path == "/api/events" and state is not None:
                    self._json_response(state.events_payload())
                    return
                if self.path.startswith("/api/events/") and self.path.endswith("/snapshot"):
                    if state is None:
                        self.send_error(404)
                        return
                    event_id = self.path.split("/")[3]
                    if not event_id.isdigit():
                        self.send_error(404)
                        return
                    snapshot = state.event_snapshot(int(event_id))
                    if snapshot is None:
                        self.send_error(404)
                        return
                    self._bytes_response(snapshot, "image/jpeg")
                    return
                if self.path == "/video.mjpg" and state is not None:
                    self._stream_video(state)
                    return
                if self.path in {"/", "/index.html"}:
                    page = Path(__file__).with_name("index.html").read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(page)))
                    self.end_headers()
                    self.wfile.write(page)
                    return
                self.send_error(404)

            def _authorized(self) -> bool:
                if auth is None:
                    return True
                header = self.headers.get("Authorization", "")
                token = ""
                scheme, _, value = header.partition(" ")
                if scheme.lower() == "bearer":
                    token = value
                elif scheme.lower() == "basic":
                    try:
                        credentials = base64.b64decode(value).decode("utf-8")
                        subject, separator, password = credentials.partition(":")
                        if separator == ":" and subject == auth_subject:
                            token = password
                    except (ValueError, UnicodeDecodeError):
                        token = ""
                principal = auth.authenticate(auth_subject, token)
                if auth.authorize(principal, "dashboard:read"):
                    return True
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="SafeSec dashboard"')
                self.end_headers()
                return False

            def _json_response(self, payload: Any) -> None:
                body = json.dumps(payload).encode("utf-8")
                self._bytes_response(body, "application/json")

            def _bytes_response(self, body: bytes, content_type: str) -> None:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _stream_video(self, dashboard: LiveDashboardState) -> None:
                self.send_response(200)
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                sequence = -1
                try:
                    while True:
                        next_frame = dashboard.wait_for_frame(sequence)
                        if next_frame is None:
                            continue
                        sequence, frame = next_frame
                        self.wfile.write(
                            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                        )
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                    return

            def log_message(self, *_: object) -> None:
                return

        self.server = ThreadingHTTPServer((host, port), Handler)

    def serve_forever(self) -> None:
        self.server.serve_forever()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
