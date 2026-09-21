from datetime import UTC, datetime, time, timedelta

from alerts.notifications import AlertService, Notification, RetryingNotificationSink
from alerts.rules import PersonPresenceRule, Schedule, TrackEventBuilder
from detection.models import BoundingBox
from detection.tracking import Track


def track(track_id: int, *, missed_frames: int = 0, label: str = "person") -> Track:
    return Track(
        track_id=track_id,
        label=label,
        box=BoundingBox(10, 10, 50, 60),
        confidence=0.9,
        last_frame_sequence=1,
        missed_frames=missed_frames,
    )


def test_track_events_emit_start_and_end_once() -> None:
    builder = TrackEventBuilder()
    when = datetime(2026, 1, 1, tzinfo=UTC)

    started = builder.observe("cam-1", (track(1),), when)
    repeated = builder.observe("cam-1", (track(1),), when + timedelta(seconds=1))
    ended = builder.observe("cam-1", (), when + timedelta(seconds=2))

    assert [event.event_type for event in started] == ["started"]
    assert repeated == ()
    assert [event.event_type for event in ended] == ["ended"]


def test_presence_rule_filters_label_confidence_and_zone() -> None:
    builder = TrackEventBuilder()
    event = builder.observe("cam-1", (track(1),), datetime(2026, 1, 1, tzinfo=UTC))[0]

    assert PersonPresenceRule("person", minimum_confidence=0.95).evaluate(event) is None
    assert PersonPresenceRule("person", zone=(100, 100, 200, 200)).evaluate(event) is None
    assert PersonPresenceRule("person").evaluate(event) is not None


def test_alert_service_suppresses_duplicate_delivery_during_cooldown() -> None:
    delivered: list[Notification] = []

    class Sink:
        def send(self, notification: Notification) -> None:
            delivered.append(notification)

    service = AlertService([Sink()], cooldown=timedelta(seconds=30))
    builder = TrackEventBuilder()
    event = builder.observe("cam-1", (track(1),), datetime(2026, 1, 1, tzinfo=UTC))[0]
    alert = PersonPresenceRule("person").evaluate(event)
    assert alert is not None

    assert service.deliver(alert, now=event.occurred_at) is True
    assert service.deliver(alert, now=event.occurred_at + timedelta(seconds=1)) is False
    assert len(delivered) == 1


def test_schedule_filters_alerts_by_time() -> None:
    builder = TrackEventBuilder()
    event = builder.observe("cam-1", (track(1),), datetime(2026, 1, 1, 12, tzinfo=UTC))[0]
    schedule = Schedule(time(9), time(17), frozenset({3}))

    assert PersonPresenceRule("work-hours", schedule=schedule).evaluate(event) is not None
    evening = event.__class__(
        event_type=event.event_type,
        camera_id=event.camera_id,
        track_id=event.track_id,
        label=event.label,
        confidence=event.confidence,
        box=event.box,
        occurred_at=datetime(2026, 1, 1, 20, tzinfo=UTC),
    )
    assert PersonPresenceRule("work-hours", schedule=schedule).evaluate(evening) is None


def test_retrying_sink_retries_transient_failure() -> None:
    attempts = 0
    waits: list[float] = []

    class FlakySink:
        def send(self, notification: Notification) -> None:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("temporary")

    alert = PersonPresenceRule("test").evaluate(
        TrackEventBuilder().observe("cam-1", (track(1),), datetime(2026, 1, 1, tzinfo=UTC))[0]
    )
    assert alert is not None
    RetryingNotificationSink(FlakySink(), max_attempts=3, sleep=waits.append).send(
        Notification(
            alert=alert,
            delivered_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    assert attempts == 3
    assert waits == [0.5, 1.0]
