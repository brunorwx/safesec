"""In-memory audit events for security-sensitive local operations."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AuditEvent:
    subject: str
    action: str
    occurred_at: datetime
    success: bool


class AuditLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._events: list[AuditEvent] = []
        if self.path is not None and self.path.exists():
            self._load()

    def record(
        self,
        subject: str,
        action: str,
        *,
        success: bool,
        occurred_at: datetime | None = None,
    ) -> None:
        event = AuditEvent(
            subject,
            action,
            (occurred_at or datetime.now(UTC)).astimezone(UTC),
            success,
        )
        self._events.append(event)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as audit_file:
                audit_file.write(json.dumps(self._serialize(event)) + "\n")
                audit_file.flush()

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def _load(self) -> None:
        assert self.path is not None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            payload = json.loads(line)
            self._events.append(
                AuditEvent(
                    subject=payload["subject"],
                    action=payload["action"],
                    occurred_at=datetime.fromisoformat(payload["occurred_at"]),
                    success=payload["success"],
                )
            )

    @staticmethod
    def _serialize(event: AuditEvent) -> dict[str, object]:
        return {
            "subject": event.subject,
            "action": event.action,
            "occurred_at": event.occurred_at.isoformat(),
            "success": event.success,
        }
