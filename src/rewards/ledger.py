"""In-memory payout ledger standing in for a database table.

`insert` behaves like a plain INSERT into a table with no unique key.
`insert_if_absent` behaves like INSERT ... ON CONFLICT (task_id) DO NOTHING.
"""
from __future__ import annotations

from .models import LedgerError, PayoutRecord


class InMemoryLedger:
    def __init__(self, fail_for: set[str] | None = None):
        self.records: list[PayoutRecord] = []
        self.fail_for: set[str] = set(fail_for or ())  # task_ids whose write fails

    def _check_failure(self, record: PayoutRecord) -> None:
        if record.task_id in self.fail_for:
            raise LedgerError(f"simulated ledger failure for {record.task_id}")

    def insert(self, record: PayoutRecord) -> None:
        self._check_failure(record)
        self.records.append(record)

    def insert_if_absent(self, record: PayoutRecord) -> bool:
        self._check_failure(record)
        if self.is_paid(record.task_id):
            return False
        self.records.append(record)
        return True

    def is_paid(self, task_id: str) -> bool:
        return any(r.task_id == task_id for r in self.records)

    def payout_count(self, task_id: str) -> int:
        return sum(1 for r in self.records if r.task_id == task_id)

    def total_credits(self) -> int:
        return sum(r.credits for r in self.records)
