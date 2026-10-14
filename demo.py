"""Walk through the DEF-001 scenario on both implementations (SYNTHETIC data).

Scenario: run of Tue 2026-10-13 09:00 UTC, three completed tasks (expected total 30 credits).
Attempt 1: the notification provider fails for T2.  Attempt 2: provider recovered, run retried.

Usage:  python demo.py
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from rewards import IMPLEMENTATIONS  # noqa: E402
from rewards.fixtures import load_tasks  # noqa: E402
from rewards.selection import SettlementContext  # noqa: E402

RUN = datetime(2026, 10, 13, 9, 0, tzinfo=timezone.utc)
EXPECTED_CREDITS = 30


def show(label, result, ctx):
    payouts = {t: ctx.ledger.payout_count(t) for t in ("T1", "T2", "T3")}
    notes = {t: ctx.notifier.sent_count(t) for t in ("T1", "T2", "T3")}
    print(f"  {label:<10} status={result.status.value:<36} credits={ctx.ledger.total_credits():>3}  "
          f"payouts={payouts}  notifications={notes}")


def main():
    tasks = load_tasks(ROOT / "fixtures" / "week_2026-10-05.json")
    for impl, settle in IMPLEMENTATIONS.items():
        print(f"\n[{impl.upper()}]")
        ctx = SettlementContext()
        ctx.notifier.fail_for = {"T2"}
        show("attempt 1", settle(tasks, RUN, ctx), ctx)
        ctx.notifier.fail_for = set()
        show("retry", settle(tasks, RUN, ctx), ctx)
        verdict = "OK" if ctx.ledger.total_credits() == EXPECTED_CREDITS else "DOUBLE PAYOUT"
        print(f"  => expected {EXPECTED_CREDITS} credits, ledger holds {ctx.ledger.total_credits()}: {verdict}")


if __name__ == "__main__":
    main()
