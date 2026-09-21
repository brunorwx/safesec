import json
import threading
from datetime import UTC, datetime
from urllib.request import urlopen

from apps.web.dashboard import DashboardSnapshot
from apps.web.server import DashboardServer
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
