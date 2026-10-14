"""Domain types for the fictional weekly rewards settlement.

SYNTHETIC: this is an assessment fixture, not a model of any live product.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

CREDITS_PER_TASK = 10  # R3
QUALIFYING_STATUS = "completed"


@dataclass(frozen=True)
class Task:
    task_id: str
    user_id: str
    status: str
    completed_at: datetime


@dataclass(frozen=True)
class PayoutRecord:
    task_id: str
    user_id: str
    credits: int
    run_id: str


class RunStatus(str, Enum):
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_NOTIFICATION_ERRORS = "COMPLETED_WITH_NOTIFICATION_ERRORS"
    COMPLETED_WITH_PAYOUT_ERRORS = "COMPLETED_WITH_PAYOUT_ERRORS"
    FAILED = "FAILED"


@dataclass
class RunResult:
    run_id: str
    status: RunStatus
    paid: list[str] = field(default_factory=list)
    already_paid: list[str] = field(default_factory=list)
    payout_errors: list[str] = field(default_factory=list)
    notification_errors: list[str] = field(default_factory=list)
    error: str | None = None


class LedgerError(Exception):
    """Simulated failure writing a payout (e.g. DB unavailable)."""


class NotificationError(Exception):
    """Simulated failure sending a notification (e.g. email provider 5xx)."""
