"""Task selection shared by both builds (R2, R3). Identical in faulty and fixed so that
the only behavioural difference between them is Failure A."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .ledger import InMemoryLedger
from .models import QUALIFYING_STATUS, Task
from .notifier import FakeNotifier, NotificationOutbox
from .window import in_window, to_utc


@dataclass
class SettlementContext:
    ledger: InMemoryLedger = field(default_factory=InMemoryLedger)
    notifier: FakeNotifier = field(default_factory=FakeNotifier)
    outbox: NotificationOutbox = field(default_factory=NotificationOutbox)


def qualifying_tasks(tasks: list[Task], window: tuple[datetime, datetime]) -> list[Task]:
    # Validate every timestamp before any money moves: one bad record rejects the run (assumption A1).
    for t in tasks:
        to_utc(t.completed_at)
    return [t for t in tasks if t.status == QUALIFYING_STATUS and in_window(t.completed_at, window)]
