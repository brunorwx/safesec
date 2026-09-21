"""Bounded local queue for status updates during connectivity loss."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Generic, TypeVar

Payload = TypeVar("Payload")


@dataclass(frozen=True, slots=True)
class QueuedUpdate(Generic[Payload]):
    payload: Payload
    queued_at: datetime


class OfflineQueue(Generic[Payload]):
    def __init__(self, *, max_size: int = 100) -> None:
        if max_size < 1:
            raise ValueError("max_size must be positive")
        self.max_size = max_size
        self._pending: list[QueuedUpdate[Payload]] = []

    @property
    def pending(self) -> tuple[QueuedUpdate[Payload], ...]:
        return tuple(self._pending)

    def enqueue(self, payload: Payload, *, queued_at: datetime | None = None) -> None:
        if len(self._pending) >= self.max_size:
            self._pending.pop(0)
        self._pending.append(
            QueuedUpdate(payload, (queued_at or datetime.now(UTC)).astimezone(UTC))
        )

    def flush(self, sender: Callable[[Payload], None]) -> int:
        delivered = 0
        while self._pending:
            update = self._pending[0]
            try:
                sender(update.payload)
            except Exception:
                break
            self._pending.pop(0)
            delivered += 1
        return delivered
