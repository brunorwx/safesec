"""Time-window scheduling for alert rules."""

from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True, slots=True)
class Schedule:
    start: time
    end: time
    weekdays: frozenset[int] = frozenset(range(7))

    def __post_init__(self) -> None:
        if not self.weekdays or any(day < 0 or day > 6 for day in self.weekdays):
            raise ValueError("weekdays must contain values from 0 through 6")

    def allows(self, moment: datetime) -> bool:
        if moment.weekday() not in self.weekdays:
            return False
        if self.start <= self.end:
            return self.start <= moment.time() <= self.end
        return moment.time() >= self.start or moment.time() <= self.end
