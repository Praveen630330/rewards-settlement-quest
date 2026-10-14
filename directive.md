# directive.md — Prevent double payout on settlement retry (final)

> Developed from `intent.md`. Synthetic assessment scenario: no live system, real money or real users.
> Repository (private, reviewer access granted): **https://github.com/Praveen630330/rewards-settlement-quest**

## 1. Objective
Make sure a weekly rewards settlement **never pays a task twice and never loses a payout** when a run is retried
after a partial failure. Back this with an automated regression check that **fails against the faulty behaviour and
passes against the corrected implementation**, and that runs as a release gate in CI.

## 2. Scope
**In scope**
- Weekly settlement: window selection, payout recording and notification dispatch.
- Defect DEF-001: a retry after a partial failure double-pays.
- Boundary and timezone cases.
- Edge cases of the same root cause: a task re-sent in a later week, conflicting duplicates, payout and notification errors in one run.

**Out of scope**
- Live systems.
- Real databases, concurrency and crash consistency (listed as gaps).
- Implementing account lifecycle or admin settings in code. Both are stated as assumptions A2 and A6 below.
- Performance testing.

## 3. Business rules (requirements)
| ID | Rule |
|---|---|
| R1 | Settlement is scheduled every **Tuesday 09:00 UTC**. |
| R2 | A run covers **[previous Monday 00:00 UTC, Monday 00:00 UTC)**, with the lower bound included and the upper excluded. The window comes from the *scheduled* run time, never from wall-clock execution time. Run 2026-10-13 09:00Z covers [2026-10-05T00:00Z, 2026-10-12T00:00Z). |
| R3 | Each task with status `completed` inside the window earns **10 test credits**. |
| R4 | A `task_id` is paid **at most once**, across duplicate inputs, retries and later runs. |
| R5 | A notification is sent **only after** that task's payout is recorded. No payout means no notification. |
| R6 | A notification failure **never reverses or repeats** a payout. The notification stays pending and is retried on its own, sent at most once successfully. |

**Assumptions:**
- **A1** Timestamps without a timezone reject the run before any payout.
- **A2 Account changes** *(assumption, not implemented or tested)*. Account status is read at the scheduled run time.
  - *Suspended:* the payout is held, with no notification. It is paid once in a later run after reinstatement (R4 still applies).
  - *Closed:* not paid, and reported as skipped.
  - The fixture treats every account as active.
- **A3** A retry re-submits the same feed for the same scheduled run.
- **A4** The R2 window means the last complete Monday-to-Monday week.
- **A5** Credits are test units.
- **A6 Admin settings** *(assumption, not implemented or tested)*.
  - *Credit-rate change:* the rate in effect at the scheduled run time applies to the whole window, so a change takes effect from the next run.
  - *Settlement paused:* the paused week is settled later by a manual run of its original scheduled time. The window comes from the schedule (R2), and R4 prevents double pay.
  - *Manual re-run of a past week:* uses the same mechanism as a retry, so nothing already paid is paid again (TC11).
- **A7 Conflicting duplicate.** If the same `task_id` appears more than once in a feed with different users, the first occurrence wins (tested by TC18).

## 4. Requirements for the deliverable
1. A runnable fixture with a **faulty** and a **fixed** implementation behind one switch (`--impl`).
2. At least 8 automated cases covering: happy path, cut-off boundary, timezone conversion, duplicate input, retry, partial failure.
3. The regression cases must **fail on faulty** and **pass on fixed**, both locally and in CI.
4. A defect report with steps to reproduce, expected vs actual, severity rationale, root cause, evidence, proposed fix and blocking release checks.
5. A release checklist with a go/no-go decision based on the evidence.
6. Synthetic data only. No secrets, hostnames or personal data in the repo.

## 5. Completion criteria
- [x] 20 cases, with expected values derived from R1–R6 ([test-cases.md](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/docs/test-cases.md))
- [x] Faulty build: the 8 regression cases fail; fixed build: 20/20 pass (local evidence)
- [x] Mutation check: no unexpected survivors
- [x] Defect report and release checklist written
- [x] CI run green for `release-gate` and expected-fail confirmed for `prove-regression` ([run](https://github.com/Praveen630330/rewards-settlement-quest/actions/runs/38529080073))
- [ ] Fresh-clone run by the candidate; candidate verification (appendix E) completed

---

## Appendix — Results and handoff

### A. Artefact links
| Artefact | Link |
|---|---|
| Runnable test project | https://github.com/Praveen630330/rewards-settlement-quest |
| Settlement code: faulty / fixed | [settlement_faulty.py](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/src/rewards/settlement_faulty.py) · [settlement_fixed.py](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/src/rewards/settlement_fixed.py) |
| Test suite (20 cases) | [tests/test_settlement.py](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/tests/test_settlement.py) |
| Cases and results table | [docs/test-cases.md](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/docs/test-cases.md) |
| Flow map and assumptions | [docs/flow.md](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/docs/flow.md) |
| Defect / root-cause report | [docs/defect-report.md](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/docs/defect-report.md) |
| Release-readiness checklist | [docs/release-checklist.md](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/docs/release-checklist.md) |
| AI collaboration log | [docs/ai-log.md](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/docs/ai-log.md) |
| Local evidence (pytest output, JUnit, mutation, demo) | [evidence/](https://github.com/Praveen630330/rewards-settlement-quest/tree/main/evidence) |
| CI workflow | [.github/workflows/regression.yml](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/.github/workflows/regression.yml) |
| CI run (release-gate + prove-regression) | [Run 38529080073](https://github.com/Praveen630330/rewards-settlement-quest/actions/runs/38529080073) — both jobs succeeded on the 20-case suite (2026-10-14) |
| Loom (≤ 5 min) | {{LOOM_URL}} |

### B. How to reproduce (about 2 minutes, Python 3.10 or later)
```bash
git clone https://github.com/Praveen630330/rewards-settlement-quest.git && cd rewards-settlement-quest
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python demo.py                          # side-by-side story: faulty 50 credits vs fixed 30
python -m pytest --impl=faulty          # expect: 8 failed, 12 passed (TC10–TC14, TC17–TC19 fail)
python -m pytest --impl=fixed           # expect: 20 passed
python scripts/mutation_check.py        # expect: 6/7 killed, no unexpected survivors
```

### C. Checks and actual results
| Check | Command | Actual result |
|---|---|---|
| Faulty build | `pytest --impl=faulty -v` | **8 failed, 12 passed**, exit 1. TC13: `expected 30 credits, got 50` |
| Fixed build | `pytest --impl=fixed -v` | **20 passed**, exit 0 |
| Mutation check | `python scripts/mutation_check.py` | **6/7 killed**. M2 survived, as expected: it's equivalent because the ledger key still enforces R4 |
| Demo | `python demo.py` | Faulty: attempt 1 FAILED with 20 credits, then the retry gives **50**. Fixed: 30, then the retry gives **30** |
| CI | GitHub Actions | Ubuntu, Python 3.12: `release-gate` **20 passed**, 8 `regression_a` collected, mutation 6/7 with no unexpected survivors; `prove-regression` **8 failed, 12 deselected** on faulty → job reports "OK: regression suite rejects the faulty build" |

Local results were captured on 2026-10-14 with Python 3.14.3 on Windows, in `evidence/`. The JUnit hostname and local paths are redacted.

### D. Release-readiness decision
- **GO** to merge the fix into the reference implementation, now that the CI run above is green. The evidence is G1, G2, G4 and G5 in the [checklist](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/docs/release-checklist.md).
- **NO-GO** for a production-like rollout until three things are in place:
  - a real DB unique constraint on `task_id`, with a test of two concurrent runs
  - payout and outbox written atomically in one transaction, with a crash-consistency test
  - an outbox monitor and a weekly reconciliation

### E. AI contribution and corrections
Claude (Claude Code, Opus 5.5) drafted the plan, code, tests and docs.

**What pre-existed:** nothing. All code, tests and docs were created for this Quest (every commit is dated 2026-10-14).

The candidate's decisions:
- plan first, before any code
- the fictional flow and stack
- choosing Failure A after reviewing the ranking walk-through
- reviewing and owning the final result

Nine corrections are logged with how each was found. The most important:
- **C2.** The first M4 mutant was *equivalent*: it could never fail. It was replaced with a real R5 risk (notify before payout), which TC14 now catches.
- **C3.** The M2 survivor was analysed rather than hidden.
- **C6.** One faulty-build figure was measured before it was stated, rather than assumed.

Full log of AI work and corrections: [docs/ai-log.md](https://github.com/Praveen630330/rewards-settlement-quest/blob/main/docs/ai-log.md).

#### Candidate verification (done by hand by the candidate, not by AI)
Each expected value was recomputed from R1–R6 without looking at the test output first, then compared with the code and results.

| # | Check | Done | My notes |
|---|---|---|---|
| V1 | Window for run 2026-10-13 09:00Z is [2026-10-05 00:00Z, 2026-10-12 00:00Z) | ☐ | {{V1_NOTES}} |
| V2 | TC05, TC06 and TC07 UTC conversions (SAST +02:00, BST +01:00) | ☐ | {{V2_NOTES}} |
| V3 | TC13 faulty result is 50 credits (walked through the faulty loop by hand) | ☐ | {{V3_NOTES}} |
| V4 | TC17, TC18 and TC19 faulty results (20 credits, 20 credits, FAILED status) | ☐ | {{V4_NOTES}} |
| V5 | `settlement_faulty.py` vs `settlement_fixed.py`: the only behavioural difference is DEF-001 | ☐ | {{V5_NOTES}} |
| V6 | Fresh clone from GitHub, new venv: faulty 8 failed / 12 passed, fixed 20 passed, mutation 6/7 | ☐ | {{V6_NOTES}} |

#### My own corrections, rejections and decisions
{{CANDIDATE_CORRECTIONS}}

### F. Limitations and remaining gaps
1. The ledger and outbox are in memory. There are no real transactions, no concurrent runs, and no crash between payout and outbox write.
2. The scheduler retry is simulated by calling `settle()` again. Real retry policies (backoff, max attempts) aren't modelled.
3. Account changes (A2) and admin settings (A6) are stated assumptions only. They aren't implemented or tested.
4. The prioritisation scores are judgement. There's no incident or frequency data.
5. Branch protection, which would make `release-gate` a required check, isn't enforced in the private repo.
6. A conflicting duplicate (same `task_id`, different users) pays the first occurrence (A7). In a real system it should fail closed for that task and be routed to ops.

### G. Handoff: next steps for whoever picks this up
1. Move the fixture to SQLite or Postgres with a `UNIQUE(task_id)` constraint. Add a two-process race test and a "crash after payout commit" test.
2. Write payout and outbox in the same transaction. Add an outbox worker with retry, backoff and a dead-letter queue.
3. Turn on a required status check for `release-gate`.
4. Add a reconciliation job: credits = 10 × distinct paid `task_id`s per window.
5. Implement A2: add an account-status input to the shared selection, a held-payout queue for suspended accounts (paid once on reinstatement, outside the normal window) and a skipped list for closed accounts, each with tests.
6. Implement A6 as configuration read at the scheduled run time, and change A7 to fail closed, reporting the conflict instead of paying the first occurrence.

### H. Effort
Actual effort: {{EFFORT}} hours. *(Candidate to record the real figure. Breakdown: planning, build and verification, docs, Loom.)*
