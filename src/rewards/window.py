"""Settlement window rules R1 and R2."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TUESDAY = 1
RUN_HOUR_UTC = 9


def to_utc(ts: datetime) -> datetime:
    """Convert an aware timestamp to UTC. Naive timestamps are rejected (assumption A1)."""
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError(f"timestamp has no timezone: {ts.isoformat()}")
    return ts.astimezone(timezone.utc)


def settlement_window(scheduled_run: datetime) -> tuple[datetime, datetime]:
    """Return [start, end) for the run scheduled at Tuesday 09:00 UTC.

    The window is derived from the *scheduled* run, never from wall-clock time,
    so a late or repeated execution settles exactly the same week.
    """
    run = to_utc(scheduled_run)
    if run.weekday() != TUESDAY or (run.hour, run.minute, run.second, run.microsecond) != (RUN_HOUR_UTC, 0, 0, 0):
        raise ValueError(f"scheduled run must be Tuesday 09:00 UTC, got {run.isoformat()}")
    end = (run - timedelta(days=1)).replace(hour=0)  # Monday 00:00 UTC, excluded
    start = end - timedelta(days=7)  # previous Monday 00:00 UTC, included
    return start, end


def in_window(ts: datetime, window: tuple[datetime, datetime]) -> bool:
    start, end = window
    return start <= to_utc(ts) < end


def run_id_for(scheduled_run: datetime) -> str:
    return "settle-" + to_utc(scheduled_run).strftime("%Y-%m-%dT%H%MZ")
