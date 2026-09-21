import base64
import json
import threading
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from apps.web.dashboard import DashboardSnapshot
from apps.web.server import DashboardServer
from gateway.authentication import ApiKeyAuthenticator
from gateway.device_api import DeviceStatus


def test_dashboard_server_serves_status_json() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    snapshot = DashboardSnapshot(DeviceStatus("device-1", True, 1, now), (), (), now)
    server = DashboardServer("127.0.0.1", 0, lambda: snapshot)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server.server_port}/api/status") as response:
            payload = json.loads(response.read())
    finally:
        server.close()
        thread.join(timeout=2)

    assert payload["device"]["id"] == "device-1"
    assert payload["device"]["online"] is True


def test_dashboard_server_requires_and_accepts_authentication() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    snapshot = DashboardSnapshot(DeviceStatus("device-1", True, 1, now), (), (), now)
    authenticator = ApiKeyAuthenticator(iterations=100_000)
    authenticator.register("dashboard", "secret-token", {"dashboard:read"})
    server = DashboardServer("127.0.0.1", 0, lambda: snapshot, authenticator=authenticator)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server.server_port}/api/status"
    try:
        with pytest.raises(HTTPError) as error:
            urlopen(url)
        assert error.value.code == 401
        credentials = base64.b64encode(b"dashboard:secret-token").decode("ascii")
        request = Request(url, headers={"Authorization": f"Basic {credentials}"})
        with urlopen(request) as response:
            assert response.status == 200
    finally:
        server.close()
        thread.join(timeout=2)
