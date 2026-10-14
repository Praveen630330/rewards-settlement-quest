"""Corrected implementation for DEF-001.

1. De-duplicate input by task_id.
2. Record payouts with an idempotency key (insert-if-absent on task_id) - R4.
3. Enqueue a notification only for a payout that was recorded - R5.
4. Deliver notifications from the outbox after the payout phase; a delivery failure
   leaves the item pending and never touches the ledger - R6.
5. A retry of the same run therefore pays nothing twice and only re-sends pending notifications.
"""
from __future__ import annotations

from datetime import datetime

from .models import CREDITS_PER_TASK, LedgerError, NotificationError, PayoutRecord, RunResult, RunStatus, Task
from .notifier import Notification
from .selection import SettlementContext, qualifying_tasks
from .window import run_id_for, settlement_window


def settle(tasks: list[Task], scheduled_run: datetime, ctx: SettlementContext) -> RunResult:
    run_id = run_id_for(scheduled_run)
    eligible = qualifying_tasks(tasks, settlement_window(scheduled_run))
    result = RunResult(run_id=run_id, status=RunStatus.COMPLETED)

    seen: set[str] = set()
    unique: list[Task] = []
    for task in eligible:  # first occurrence of a task_id wins
        if task.task_id not in seen:
            seen.add(task.task_id)
            unique.append(task)

    # Phase 1: payouts
    for task in unique:
        try:
            inserted = ctx.ledger.insert_if_absent(PayoutRecord(task.task_id, task.user_id, CREDITS_PER_TASK, run_id))
        except LedgerError:
            result.payout_errors.append(task.task_id)
            continue
        if inserted:
            result.paid.append(task.task_id)
            ctx.outbox.enqueue(Notification(task.task_id, task.user_id, CREDITS_PER_TASK))
        else:
            result.already_paid.append(task.task_id)

    # Phase 2: notifications (includes items still pending from earlier attempts)
    for notification in ctx.outbox.pending():
        try:
            ctx.notifier.send(notification)
        except NotificationError:
            result.notification_errors.append(notification.task_id)
            continue
        ctx.outbox.mark_sent(notification.task_id)

    if result.payout_errors:
        result.status = RunStatus.COMPLETED_WITH_PAYOUT_ERRORS
    elif result.notification_errors:
        result.status = RunStatus.COMPLETED_WITH_NOTIFICATION_ERRORS
    return result
