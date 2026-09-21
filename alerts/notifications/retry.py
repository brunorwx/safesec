"""Bounded notification retry policy."""

import time
from collections.abc import Callable

from .service import Notification, NotificationSink


class RetryingNotificationSink:
    def __init__(
        self,
        sink: NotificationSink,
        *,
        max_attempts: int = 3,
        backoff_seconds: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_attempts < 1 or backoff_seconds < 0:
            raise ValueError("retry limits must be valid")
        self.sink = sink
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep

    def send(self, notification: Notification) -> None:
        for attempt in range(self.max_attempts):
            try:
                self.sink.send(notification)
                return
            except Exception:
                if attempt == self.max_attempts - 1:
                    raise
                self.sleep(self.backoff_seconds * (attempt + 1))
