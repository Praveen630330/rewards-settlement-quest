# Test cases and results

> SYNTHETIC data. Run under test: **Tue 2026-10-13 09:00 UTC**, window **[2026-10-05T00:00Z, 2026-10-12T00:00Z)**.
> "Fixture T1–T3" = `fixtures/week_2026-10-05.json`: three completed tasks inside the window (expected total 30 credits).
> Actual results from `evidence/pytest-faulty.txt` and `evidence/pytest-fixed.txt` (captured 2026-10-14, Python 3.14.3, Windows).

| TC | Category | Rule | Input | Expected outcome | Faulty build | Fixed build |
|---|---|---|---|---|---|---|
| 00 | Window derivation | R1 R2 | Scheduled run 2026-10-13 09:00Z | Window = [10-05 00:00Z, 10-12 00:00Z) | PASS | PASS |
| 16 | Window derivation | R1 R2 | "Run" at 2026-10-13 09:07Z (late execution time passed as schedule) | Rejected — window only derives from a Tuesday 09:00 UTC schedule | PASS | PASS |
| 01 | **Happy path** | R3 R5 | Fixture T1–T3 | 3 payouts, 30 credits, 3 notifications, status COMPLETED | PASS | PASS |
| 02 | **Cut-off boundary** (lower) | R2 | Completed 2026-10-05T00:00:00Z | Paid (lower bound inclusive) | PASS | PASS |
| 03 | **Cut-off boundary** (upper) | R2 | Completed 2026-10-12T00:00:00Z; then 10-20 run | Not paid on 10-13; paid once on 10-20 | PASS | PASS |
| 04 | Cut-off boundary | R2 | Completed 2026-10-11T23:59:59.999999Z | Paid | PASS | PASS |
| 05 | **Timezone conversion** | R2 | 2026-10-12T01:30+02:00 (SAST) = 10-11T23:30Z | Paid | PASS | PASS |
| 06 | Timezone conversion | R2 | 2026-10-05T01:00+02:00 (SAST) = 10-04T23:00Z | Not paid (previous week) | PASS | PASS |
| 07 | Timezone conversion (DST zone) | R2 | 2026-10-12T00:30 Europe/London (BST, +01:00) = 10-11T23:30Z | Paid | PASS | PASS |
| 08 | Invalid input | A1 | Fixture + one timestamp with no timezone | Run rejected (ValueError); 0 payouts, 0 notifications | PASS | PASS |
| 09 | Eligibility | R3 | status=`cancelled` inside window | Not paid, not notified | PASS | PASS |
| 15 | Duplicate across runs | R2 R4 | 10-13 run with T1–T3; 10-20 run with T1–T3 re-sent + new T4 | 40 credits total, each task paid once | PASS | PASS |
| 10 | **Duplicate input** | R4 | T1 twice in the same feed | 1 payout (10 credits), 1 notification | **FAIL** — 20 credits | PASS |
| 11 | **Retry** (after success) | R4 | Same run executed twice | Still 30 credits; 2nd run pays nothing; 1 notification each | **FAIL** — 60 credits | PASS |
| 12 | **Partial failure** (notification) | R5 R6 | Notifier fails for T2 | 30 credits kept; T2 notification pending; status COMPLETED_WITH_NOTIFICATION_ERRORS | **FAIL** — 20 credits, status FAILED, T3 never paid | PASS |
| 13 | **Retry after partial failure — core DEF-001** | R4 R5 R6 | TC12, then retry with notifier healthy | 30 credits; each task paid once and notified once; retry status COMPLETED | **FAIL** — 50 credits (T1, T2 paid twice) | PASS |
| 14 | Partial failure (payout) + retry | R4 R5 | Ledger fails for T3, then retry | Attempt 1: COMPLETED_WITH_PAYOUT_ERRORS, T3 not paid **and not notified**; retry: 30 credits, each once | **FAIL** — attempt 1 status FAILED; measured retry total 50 credits | PASS |

**Totals:** 17 cases. Fixed build 17/17 pass. Faulty build 12 pass / 5 fail — exactly the five `regression_a` cases.
The 12 cases that pass on both builds show the faulty build differs only in the DEF-001 behaviour (window,
timezone and eligibility logic are shared), so the failures point at the defect, not at unrelated noise.

## How each expected value was derived
- Credits = 10 × number of **distinct** `task_id`s that are `completed` and inside the window (R3, R4).
- Window membership uses the UTC instant: `start <= completed_at_utc < end` (R2).
- Notification count per task must equal its payout count, and both must be 1 (R4, R5).
- Faulty actuals for TC13: attempt 1 pays T1 (10), pays T2 (20), T2 notification throws → job FAILED, T3 skipped; retry pays T1, T2, T3 again → 50. Matches measured value.

## Test-quality check (mutation)
`scripts/mutation_check.py` re-introduces plausible partial fixes into the fixed build — see `evidence/mutation-check.txt`.

| Mutant | Result | Caught by |
|---|---|---|
| M1 no idempotency key | Killed | TC11, TC13, TC14 |
| M2 input de-dup removed | Survived — *equivalent*: the ledger key still blocks the duplicate payout | — |
| M3 notification failure aborts run | Killed | TC12, TC13 |
| M4 notification enqueued before payout recorded | Killed | TC14 |
| M5 outbox never marks sent | Killed | TC11, TC13, TC14 |
| M6 upper boundary inclusive | Killed | TC03 |
| M7 naive timestamps treated as UTC | Killed | TC08 |
