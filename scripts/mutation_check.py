"""Mutation check: does the suite catch *partial* or regressed fixes, not just the one faulty build?

Each mutant re-introduces one plausible mistake into a temporary copy of the fixed build and runs
the full suite against it. A mutant is "killed" when at least one test fails.

Usage:  python scripts/mutation_check.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXED = "src/rewards/settlement_fixed.py"
WINDOW = "src/rewards/window.py"

MUTANTS = [
    ("M1 no idempotency key (plain insert)", FIXED,
     "inserted = ctx.ledger.insert_if_absent(PayoutRecord(task.task_id, task.user_id, CREDITS_PER_TASK, run_id))",
     "ctx.ledger.insert(PayoutRecord(task.task_id, task.user_id, CREDITS_PER_TASK, run_id)); inserted = True"),
    # Expected to survive: the ledger idempotency key still blocks the duplicate payout, so behaviour
    # is unchanged (defence in depth). Kept to document that de-dup alone is not what protects R4.
    ("M2 input de-duplication removed [equivalent - expected to survive]", FIXED,
     "if task.task_id not in seen:", "if True:"),
    ("M3 notification failure aborts the run", FIXED,
     "except NotificationError:", "except ZeroDivisionError:"),
    ("M4 notification enqueued before payout is recorded", FIXED,
     "        try:\n            inserted = ctx.ledger.insert_if_absent(",
     "        ctx.outbox.enqueue(Notification(task.task_id, task.user_id, CREDITS_PER_TASK))\n"
     "        try:\n            inserted = ctx.ledger.insert_if_absent("),
    ("M5 outbox never marks sent (re-notify on retry)", FIXED,
     "ctx.outbox.mark_sent(notification.task_id)", "pass"),
    ("M6 upper boundary inclusive (<= end)", WINDOW,
     "return start <= to_utc(ts) < end", "return start <= to_utc(ts) <= end"),
    ("M7 naive timestamps silently treated as UTC", WINDOW,
     'raise ValueError(f"timestamp has no timezone: {ts.isoformat()}")', "ts = ts.replace(tzinfo=timezone.utc)"),
]


def run_mutant(name: str, rel: str, old: str, new: str) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for item in ("src", "tests", "fixtures", "pyproject.toml"):
            src = ROOT / item
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, work / item)
        target = work / rel
        text = target.read_text(encoding="utf-8").replace("\r\n", "\n")  # tolerate CRLF checkouts
        if old not in text:
            raise SystemExit(f"{name}: anchor text not found in {rel} - update the mutant definition")
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--impl=fixed", "-q", "-p", "no:cacheprovider"],
            cwd=work, capture_output=True, text=True,
        )
        failed = [line.split("::")[1].split(" ")[0] for line in proc.stdout.splitlines() if line.startswith("FAILED")]
        killed = proc.returncode == 1
        print(f"{'KILLED  ' if killed else 'SURVIVED'} {name}")
        for test in failed:
            print(f"           caught by {test}")
        return killed


def main() -> int:
    results = {m[0]: run_mutant(*m) for m in MUTANTS}
    unexpected = [name for name, killed in results.items() if not killed and "[equivalent" not in name]
    print(f"\n{sum(results.values())}/{len(results)} mutants killed; unexpected survivors: {unexpected or 'none'}")
    return 1 if unexpected else 0


if __name__ == "__main__":
    sys.exit(main())
