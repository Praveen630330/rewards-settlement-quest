"""Regression suite for the fictional weekly rewards settlement (SYNTHETIC data only).

Rules under test (see directive.md):
  R1 run Tuesday 09:00 UTC   R2 window [prev Mon 00:00Z, Mon 00:00Z)   R3 10 credits per completed task
  R4 task_id paid at most once   R5 notify only after successful payout   R6 notification failure never reverses/repeats payout

Tests marked `regression_a` guard DEF-001 (retry after partial failure double-pays).
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from rewards.fixtures import load_tasks
from rewards.models import RunStatus, Task
from rewards.window import settlement_window

UTC = timezone.utc
SAST = timezone(timedelta(hours=2))  # South Africa, no DST
RUN = datetime(2026, 10, 13, 9, 0, tzinfo=UTC)  # Tuesday
NEXT_RUN = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "week_2026-10-05.json"


def task(task_id, completed_at, status="completed", user_id="user-a"):
    return Task(task_id, user_id, status, completed_at)


def three_tasks():
    return load_tasks(FIXTURE)  # T1, T2, T3 all inside the 2026-10-05 window


def assert_paid_once_each(ctx, task_ids):
    for task_id in task_ids:
        assert ctx.ledger.payout_count(task_id) == 1, f"{task_id} paid {ctx.ledger.payout_count(task_id)} times, expected once"


def assert_notified_once_each(ctx, task_ids):
    for task_id in task_ids:
        assert ctx.notifier.sent_count(task_id) == 1, f"{task_id} notified {ctx.notifier.sent_count(task_id)} times, expected once"


# --- Window derivation (R1, R2) ---------------------------------------------------------

def test_tc00_window_is_previous_monday_to_monday_derived_from_scheduled_run():
    assert settlement_window(RUN) == (datetime(2026, 10, 5, tzinfo=UTC), datetime(2026, 10, 12, tzinfo=UTC))


def test_tc16_window_rejects_run_that_is_not_tuesday_0900_utc():
    late_execution = RUN + timedelta(minutes=7)
    with pytest.raises(ValueError):
        settlement_window(late_execution)


# --- Happy path, boundaries, timezones, eligibility -------------------------------------

def test_tc01_happy_path_three_tasks_pay_30_and_notify_each(settle, ctx):
    result = settle(three_tasks(), RUN, ctx)
    assert result.status == RunStatus.COMPLETED
    assert ctx.ledger.total_credits() == 30
    assert_paid_once_each(ctx, ["T1", "T2", "T3"])
    assert_notified_once_each(ctx, ["T1", "T2", "T3"])


def test_tc02_lower_boundary_monday_0000_utc_is_included(settle, ctx):
    settle([task("B1", datetime(2026, 10, 5, 0, 0, tzinfo=UTC))], RUN, ctx)
    assert ctx.ledger.payout_count("B1") == 1


def test_tc03_upper_boundary_monday_0000_utc_is_excluded_and_paid_next_week(settle, ctx):
    boundary = task("B2", datetime(2026, 10, 12, 0, 0, tzinfo=UTC))
    settle([boundary], RUN, ctx)
    assert ctx.ledger.payout_count("B2") == 0, "upper bound must be excluded from the 2026-10-13 run"
    settle([boundary], NEXT_RUN, ctx)
    assert ctx.ledger.payout_count("B2") == 1, "boundary task must be paid by the 2026-10-20 run"


def test_tc04_last_microsecond_before_upper_boundary_is_included(settle, ctx):
    settle([task("B3", datetime(2026, 10, 11, 23, 59, 59, 999999, tzinfo=UTC))], RUN, ctx)
    assert ctx.ledger.payout_count("B3") == 1


def test_tc05_sast_local_monday_0130_is_sunday_2330_utc_and_included(settle, ctx):
    settle([task("Z1", datetime(2026, 10, 12, 1, 30, tzinfo=SAST))], RUN, ctx)
    assert ctx.ledger.payout_count("Z1") == 1


def test_tc06_sast_local_monday_0100_is_sunday_2300_utc_previous_week_and_excluded(settle, ctx):
    settle([task("Z2", datetime(2026, 10, 5, 1, 0, tzinfo=SAST))], RUN, ctx)
    assert ctx.ledger.payout_count("Z2") == 0


def test_tc07_london_bst_monday_0030_is_sunday_2330_utc_and_included(settle, ctx):
    london = datetime(2026, 10, 12, 0, 30, tzinfo=ZoneInfo("Europe/London"))  # BST (UTC+1) until 2026-10-25
    assert london.utcoffset() == timedelta(hours=1)
    settle([task("Z3", london)], RUN, ctx)
    assert ctx.ledger.payout_count("Z3") == 1


def test_tc08_timestamp_without_timezone_rejects_run_before_any_payout(settle, ctx):
    tasks = three_tasks() + [task("N1", datetime(2026, 10, 7, 12, 0))]  # naive
    with pytest.raises(ValueError):
        settle(tasks, RUN, ctx)
    assert ctx.ledger.total_credits() == 0
    assert ctx.notifier.sent == []


def test_tc09_non_completed_task_in_window_is_not_paid(settle, ctx):
    settle([task("C1", datetime(2026, 10, 7, 12, 0, tzinfo=UTC), status="cancelled")], RUN, ctx)
    assert ctx.ledger.payout_count("C1") == 0
    assert ctx.notifier.sent == []


def test_tc15_previous_week_tasks_resent_in_next_feed_are_not_paid_again(settle, ctx):
    week1 = three_tasks()
    settle(week1, RUN, ctx)
    new = task("T4", datetime(2026, 10, 14, 10, 0, tzinfo=UTC))
    settle(week1 + [new], NEXT_RUN, ctx)
    assert ctx.ledger.total_credits() == 40
    assert_paid_once_each(ctx, ["T1", "T2", "T3", "T4"])


# --- DEF-001 regression: duplicates, retries, partial failure (R4, R5, R6) ---------------

@pytest.mark.regression_a
def test_tc10_duplicate_task_id_in_input_is_paid_once(settle, ctx):
    t1 = task("T1", datetime(2026, 10, 6, 8, 15, tzinfo=UTC))
    settle([t1, t1], RUN, ctx)
    assert ctx.ledger.total_credits() == 10, f"expected 10 credits, got {ctx.ledger.total_credits()}"
    assert_notified_once_each(ctx, ["T1"])


@pytest.mark.regression_a
def test_tc11_rerun_after_successful_run_pays_and_notifies_nothing_new(settle, ctx):
    settle(three_tasks(), RUN, ctx)
    second = settle(three_tasks(), RUN, ctx)
    assert ctx.ledger.total_credits() == 30, f"expected 30 credits, got {ctx.ledger.total_credits()}"
    assert second.paid == []
    assert_notified_once_each(ctx, ["T1", "T2", "T3"])


@pytest.mark.regression_a
def test_tc12_notification_failure_keeps_all_payouts_and_leaves_notification_pending(settle, ctx):
    ctx.notifier.fail_for = {"T2"}
    result = settle(three_tasks(), RUN, ctx)
    assert ctx.ledger.total_credits() == 30, f"expected 30 credits, got {ctx.ledger.total_credits()}"
    assert_paid_once_each(ctx, ["T1", "T2", "T3"])
    assert result.status == RunStatus.COMPLETED_WITH_NOTIFICATION_ERRORS, f"got {result.status}"
    assert result.notification_errors == ["T2"]
    assert ctx.notifier.sent_count("T2") == 0


@pytest.mark.regression_a
def test_tc13_retry_after_notification_failure_does_not_pay_twice(settle, ctx):
    """Core DEF-001 reproduction: notification fails -> run retried -> must not double-pay."""
    ctx.notifier.fail_for = {"T2"}
    settle(three_tasks(), RUN, ctx)
    ctx.notifier.fail_for = set()  # provider recovers
    retry = settle(three_tasks(), RUN, ctx)
    assert ctx.ledger.total_credits() == 30, f"expected 30 credits, got {ctx.ledger.total_credits()}"
    assert_paid_once_each(ctx, ["T1", "T2", "T3"])
    assert_notified_once_each(ctx, ["T1", "T2", "T3"])
    assert retry.status == RunStatus.COMPLETED


@pytest.mark.regression_a
def test_tc14_payout_failure_is_not_notified_and_retry_pays_it_once(settle, ctx):
    ctx.ledger.fail_for = {"T3"}
    first = settle(three_tasks(), RUN, ctx)
    assert first.status == RunStatus.COMPLETED_WITH_PAYOUT_ERRORS, f"got {first.status}"
    assert ctx.ledger.payout_count("T3") == 0
    assert ctx.notifier.sent_count("T3") == 0, "R5: no notification without a successful payout"
    ctx.ledger.fail_for = set()  # ledger recovers
    settle(three_tasks(), RUN, ctx)
    assert ctx.ledger.total_credits() == 30, f"expected 30 credits, got {ctx.ledger.total_credits()}"
    assert_paid_once_each(ctx, ["T1", "T2", "T3"])
    assert_notified_once_each(ctx, ["T1", "T2", "T3"])


@pytest.mark.regression_a
def test_tc17_task_resent_next_week_with_new_in_window_timestamp_is_not_paid_again(settle, ctx):
    settle([task("T1", datetime(2026, 10, 6, 8, 15, tzinfo=UTC))], RUN, ctx)
    resent = task("T1", datetime(2026, 10, 14, 10, 0, tzinfo=UTC))  # same task_id, inside the 10-20 window
    settle([resent], NEXT_RUN, ctx)
    assert ctx.ledger.total_credits() == 10, f"expected 10 credits, got {ctx.ledger.total_credits()}"
    assert_paid_once_each(ctx, ["T1"])
    assert_notified_once_each(ctx, ["T1"])


@pytest.mark.regression_a
def test_tc18_same_task_id_for_two_users_in_one_feed_pays_first_occurrence_once(settle, ctx):
    when = datetime(2026, 10, 6, 8, 15, tzinfo=UTC)
    settle([task("T1", when, user_id="user-a"), task("T1", when, user_id="user-b")], RUN, ctx)
    assert ctx.ledger.total_credits() == 10, f"expected 10 credits, got {ctx.ledger.total_credits()}"
    assert [r.user_id for r in ctx.ledger.records] == ["user-a"], "assumption A7: first occurrence wins"
    assert [n.user_id for n in ctx.notifier.sent] == ["user-a"]


@pytest.mark.regression_a
def test_tc19_payout_and_notification_failures_in_one_run_are_both_reported_and_retry_settles_once(settle, ctx):
    ctx.ledger.fail_for = {"T3"}
    ctx.notifier.fail_for = {"T2"}
    first = settle(three_tasks(), RUN, ctx)
    assert first.status == RunStatus.COMPLETED_WITH_PAYOUT_ERRORS, f"got {first.status}"
    assert first.payout_errors == ["T3"]
    assert first.notification_errors == ["T2"]
    assert ctx.ledger.total_credits() == 20, f"expected 20 credits, got {ctx.ledger.total_credits()}"
    assert ctx.notifier.sent_count("T3") == 0, "R5: no notification without a successful payout"
    ctx.ledger.fail_for = set()  # both recover
    ctx.notifier.fail_for = set()
    settle(three_tasks(), RUN, ctx)
    assert ctx.ledger.total_credits() == 30, f"expected 30 credits, got {ctx.ledger.total_credits()}"
    assert_paid_once_each(ctx, ["T1", "T2", "T3"])
    assert_notified_once_each(ctx, ["T1", "T2", "T3"])
