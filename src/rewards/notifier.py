"""Fake notifier and notification outbox."""
from __future__ import annotations

from dataclasses import dataclass

from .models import NotificationError


@dataclass(frozen=True)
class Notification:
    task_id: str
    user_id: str
    credits: int


class FakeNotifier:
    def __init__(self, fail_for: set[str] | None = None):
        self.sent: list[Notification] = []
        self.fail_for: set[str] = set(fail_for or ())  # task_ids whose send fails

    def send(self, notification: Notification) -> None:
        if notification.task_id in self.fail_for:
            raise NotificationError(f"simulated notification failure for {notification.task_id}")
        self.sent.append(notification)

    def sent_count(self, task_id: str) -> int:
        return sum(1 for n in self.sent if n.task_id == task_id)


class NotificationOutbox:
    """Durable queue of notifications owed for recorded payouts (used by the fixed build)."""

    def __init__(self):
        self._items: dict[str, Notification] = {}
        self._sent: set[str] = set()

    def enqueue(self, notification: Notification) -> None:
        self._items.setdefault(notification.task_id, notification)

    def pending(self) -> list[Notification]:
        return [n for task_id, n in self._items.items() if task_id not in self._sent]

    def mark_sent(self, task_id: str) -> None:
        self._sent.add(task_id)
