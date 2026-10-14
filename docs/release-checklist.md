# Release-readiness checklist — DEF-001 fix

> Scope: the reference settlement implementation in this repo (SYNTHETIC). Not a live system.

## Gates
| # | Check | How verified | Result (2026-10-14) |
|---|---|---|---|
| G1 | Full suite passes on the fixed build | `pytest --impl=fixed` → `evidence/pytest-fixed.txt` | ✅ 17/17 passed (local, Windows, Py 3.14.3) |
| G2 | Regression tests fail on the faulty build (the tests really detect the defect) | `pytest --impl=faulty` → `evidence/pytest-faulty.txt` | ✅ TC10–TC14 fail, all other 12 pass |
| G3 | At least 5 `regression_a` cases present and not skipped | CI step "Regression cases must exist" | ✅ 5 collected locally; ☐ CI run to be confirmed |
| G4 | No unexpected mutant survivors | `scripts/mutation_check.py` → `evidence/mutation-check.txt` | ✅ 6/7 killed; M2 survivor is equivalent (explained) |
| G5 | Mandatory case types covered: happy, cut-off, timezone, duplicate, retry, partial failure | `docs/test-cases.md` | ✅ |
| G6 | CI green on `release-gate` and expected-fail confirmed on `prove-regression` | GitHub Actions | ☐ **Pending** — needs push to the private repo; link to be added to `directive.md` |
| G7 | Fresh-clone setup works for someone else | Clone → venv → `pip install -r requirements.txt` → `pytest` | ☐ Pending (to be done after push) |
| G8 | No real data, secrets or internal hostnames in the repo | Manual grep; JUnit hostname and local paths redacted in `evidence/` | ✅ |
| G9 | Required status check / branch protection enforcing G6 | GitHub repo settings | ☐ Recommended; may need a paid GitHub plan for private repos — **not enforced** |

## Decision
**GO** — merge the fix into the reference implementation, *once G6 and G7 are ticked*. Basis: G1, G2, G4 and G5 are evidenced locally, and the fix is narrow (one module) with no change to window or eligibility logic (12 shared cases unchanged).

**NO-GO for any production-like rollout** of this design until these are closed:
1. A real database **unique constraint** on `task_id`, plus a test of two concurrent runs racing on the same task (not modelled by the in-memory ledger).
2. A crash-consistency test: the process dies after the payout commit but before the outbox write. This needs the payout and outbox row in **one database transaction**.
3. An outbox monitor/alert for notifications stuck in pending, plus a weekly reconciliation report.

## Monitoring to add after release (recommendation, not built)
- Alert if a `task_id` appears more than once in the payout table. This should be impossible with the constraint, so the alert is a canary for it being dropped.
- Alert if outbox pending items are older than 1 hour.
- Weekly reconciliation: credits paid = 10 × distinct qualifying tasks in the window.
