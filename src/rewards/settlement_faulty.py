"""FAULTY reference implementation - reproduces DEF-001 (Failure A).

Pays and notifies in one loop with no idempotency key. Any exception (including a
notification failure) aborts the job as FAILED, and the scheduler's retry then pays
every already-paid task again.

Do not "fix" this file: the regression suite must keep failing against it.
"""
from __future__ import annotations

from datetime import datetime

from .models import CREDITS_PER_TASK, PayoutRecord, RunResult, RunStatus, Task
from .notifier import Notification
from .selection import SettlementContext, qualifying_tasks
from .window import run_id_for, settlement_window


def settle(tasks: list[Task], scheduled_run: datetime, ctx: SettlementContext) -> RunResult:
    run_id = run_id_for(scheduled_run)
    eligible = qualifying_tasks(tasks, settlement_window(scheduled_run))
    result = RunResult(run_id=run_id, status=RunStatus.COMPLETED)
    try:
        for task in eligible:  # BUG: duplicates in input are not removed
            ctx.ledger.insert(PayoutRecord(task.task_id, task.user_id, CREDITS_PER_TASK, run_id))  # BUG: no idempotency key
            result.paid.append(task.task_id)
            ctx.notifier.send(Notification(task.task_id, task.user_id, CREDITS_PER_TASK))  # BUG: notify inside the payout unit of work
    except Exception as exc:  # job runner marks the whole run FAILED -> operator/scheduler retries the run
        result.status = RunStatus.FAILED
        result.error = str(exc)
    return result
