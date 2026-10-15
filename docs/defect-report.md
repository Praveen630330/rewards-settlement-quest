# DEF-001 — Retrying a settlement run after a notification failure pays tasks twice

| Field | Value |
|---|---|
| Component | Weekly rewards settlement — payout + notification step |
| Build affected | `--impl=faulty` (reference faulty build) |
| Fixed in | `--impl=fixed` (`src/rewards/settlement_fixed.py`) |
| Severity | **S1 – Critical** |
| Priority | **P1 – block release** |
| Rules violated | R4 (task paid at most once), R5 (notify only after successful payout), R6 (notification failure never reverses/repeats a payout) |
| Status | Fixed in reference build; regression tests TC10–TC14 and TC17–TC19 in CI |

## Summary
When a notification fails part-way through a settlement run, the whole run is marked FAILED. The retry then
re-executes payouts for every task already paid, because payouts carry no idempotency key. Users receive
duplicate credits and duplicate notifications. Tasks after the failure point are left unpaid until a retry happens.

## Steps to reproduce
1. `python -m venv .venv` then activate it, and `pip install -r requirements.txt`
2. `python demo.py`  *(or the automated case: `python -m pytest --impl=faulty -k tc13 -v`)*
3. Scenario inside the demo/test:
   - Settlement run scheduled **Tue 2026-10-13 09:00 UTC**; feed = T1, T2, T3, all completed inside `[2026-10-05T00:00Z, 2026-10-12T00:00Z)`.
   - Notification provider fails for T2 on attempt 1.
   - Provider recovers; the same run is retried.

## Expected vs actual
| | Expected (R3–R6) | Actual — faulty build (measured) |
|---|---|---|
| Attempt 1 status | COMPLETED_WITH_NOTIFICATION_ERRORS | **FAILED** |
| Attempt 1 credits | 30 (T1, T2, T3 each paid once) | **20** (T3 never reached) |
| After retry — credits | **30** | **50** |
| After retry — payouts per task | T1 = 1, T2 = 1, T3 = 1 | **T1 = 2, T2 = 2**, T3 = 1 |
| After retry — notifications per task | 1, 1, 1 | **2**, 1, 1 |

Related symptoms from the same root cause (all measured, see `docs/test-cases.md`):
- Duplicate `task_id` in a single feed → 20 credits instead of 10 (TC10).
- Re-running a run that *succeeded* → 60 credits instead of 30 (TC11).
- Ledger failure on T3 → whole run FAILED; retry pays T1 and T2 again → 50 credits (TC14).
- A task re-sent in the next week's feed with a new in-window timestamp → paid again, 20 credits instead of 10 (TC17).
- The same `task_id` for two users in one feed → both paid, 20 credits instead of 10 (TC18).
- Payout failure on T3 plus notification failure on T2 → whole run FAILED instead of reporting both errors (TC19).

## Evidence
- `evidence/demo.txt` — side-by-side faulty vs fixed run of the scenario.
- `evidence/pytest-faulty.txt` — 8 failed / 12 passed; e.g. `AssertionError: expected 30 credits, got 50` (TC13).
- `evidence/pytest-fixed.txt` — 20 passed.
- `evidence/junit-*.xml` — machine-readable results.
- GitHub Actions run — see the links in `directive.md`.

## Root cause
1. **No idempotency key on payouts.** `ledger.insert()` is a plain append; nothing records that a `task_id` is already settled, so any re-execution pays again. Duplicates in the feed are not removed.
2. **Payout and notification share one unit of work.** `notifier.send()` runs inside the payout loop. Its exception escapes to the job runner, which marks the *run* FAILED even though money has already moved.
3. **Retry granularity is the whole run.** The FAILED status invites a full re-run (correct behaviour for a scheduler), and (1) makes a full re-run unsafe.

Item 3 is not a bug by itself. It is the trigger that turns (1) and (2) into a financial loss.

## Severity rationale
- **Impact – high.** Credits are paid out more than once (here +67%: 50 vs 30), and that is hard to claw back. Users get confusing duplicate messages. If nobody retries, tasks after the failure point go unpaid, which means support tickets.
- **Likelihood – medium-high.** Notification providers have transient failures, and retries are standard practice. No special input is needed: any single notification error triggers it.
- **Detectability – low.** Overpaid users rarely report it, and a retried run ends COMPLETED. It would only surface in finance reconciliation.
- Taken together, it's S1/P1: silent money loss triggered by routine operational events.

## Proposed fix (implemented in `settlement_fixed.py`)
1. **Idempotent payout write** — `insert_if_absent` keyed on `task_id`. In a real database this is a **unique constraint** on `task_id` with `INSERT … ON CONFLICT DO NOTHING`.
2. **De-duplicate the feed** by `task_id`. This is defence in depth; mutation M2 shows the key alone already protects R4.
3. **Separate phases.** Phase 1 records payouts. Phase 2 sends notifications from an **outbox**. A notification is enqueued only when its payout was recorded (R5).
4. **Notification failure is not a run failure.** The item stays pending, the status is `COMPLETED_WITH_NOTIFICATION_ERRORS`, and the next attempt sends only pending items (R6).
5. **Payout failure** is reported per task (`COMPLETED_WITH_PAYOUT_ERRORS`), with no notification, and a retry pays that task once.

## Release checks that block this failure
| Check | Blocks |
|---|---|
| CI `release-gate`: full suite on the candidate build must be 20/20 | Any return of double-pay, notify-before-pay or a boundary regression |
| CI `release-gate`: at least 8 `regression_a` cases collected and not skipped | Someone deleting or skipping the guard tests |
| CI `release-gate`: mutation check, no unexpected survivors | Weakened assertions that would let partial fixes through |
| CI `prove-regression`: suite must FAIL on the faulty build | Tests that silently stop exercising the defect |
| Pre-release reconciliation (manual/scripted): `sum(credits) == 10 × count(distinct task_id)` per run | Double-pay paths the fixture doesn't model (see gaps) |
| Schema review: unique constraint on `payout.task_id` exists | Losing the idempotency guarantee in a real database |
