# AI collaboration log

**Tool:** Claude Code (model: Claude Opus 5.5), used in one working session on 2026-10-14.
**Rule for this log:** only events that actually happened. Nothing reconstructed or invented.

## Who did what
| Area | Candidate (Praveen) | AI (Claude) |
|---|---|---|
| Approach | Asked for a plan-first approach before any code; required a walk-through of failure options before choosing | Drafted the plan, scoring rubric mapping and ranking table |
| Scenario & stack | Chose the fictional rewards flow, Python + pytest, private GitHub repo + CI | Proposed the options |
| Failure choice | Reviewed the ranking walk-through and **chose Failure A** | Proposed criteria, weights and initial scores (judgement, not data) |
| Code & tests | Reviews, runs and owns the result (see the verification section below) | Wrote the fixture, faulty/fixed builds, 17 tests, mutation check, demo and CI workflow |
| Docs | Final edits, Loom recording, submission | Drafted docs, intent and directive |

## Corrections and rejections made during the session
| # | What the AI first produced | Problem found | How it was found | Correction |
|---|---|---|---|---|
| C1 | De-duplication written as a nested reverse-dict one-liner | Correct but hard to review, and order semantics were non-obvious | Self-review before first run | Replaced with an explicit loop, "first occurrence wins" |
| C2 | Mutation **M4** = "enqueue notification even when already paid" | **Equivalent mutant.** The outbox is keyed by `task_id`, so it could never fail a test and proved nothing. It survived. | Ran `mutation_check.py`, investigated why it survived | Replaced with "enqueue notification *before* the payout is recorded" (a real R5 risk). Now killed by TC14. |
| C3 | Mutation **M2** (de-dup removed) survived | Investigated rather than tweaking a test to kill it | Same run | Judged equivalent: the ledger key already enforces R4. Kept it, **labelled** as expected-survivor, and the script fails only on *unexpected* survivors |
| C4 | Plan listed TC15 (cross-week duplicate) as "pass/FAIL depending on input" | Unresolved expectation | While writing the tests | Resolved: the window filter excludes last week's tasks in both builds, so TC15 passes on both. Reframed as a "feed re-sends previous week" guard |
| C5 | Captured evidence (`junit-*.xml`, pytest output) | Contained the local machine hostname and user path (internal info) | Grep of evidence before commit | Redacted to `hostname="redacted"` and `<repo>` |
| C6 | Defect report claims for TC14 faulty behaviour | The test stops at its first assertion, so the "50 credits after retry" figure was derived, not measured | Self-check while drafting | Measured it with a script before stating it: faulty attempt 1 = FAILED/20, retry = 50 |
| C7 | `zoneinfo("Europe/London")` in TC07 | Windows Python has no system tz database, so the test would fail for a Windows reviewer | Known platform behaviour | Pinned `tzdata` in `requirements.txt`; TC07 also asserts the +01:00 offset so a wrong tz database fails loudly |
| C8 | Mutation script anchors written assuming LF line endings | `git add` warned files would be checked out as CRLF on Windows, so the multi-line M4 anchor would not match and the script would abort for a Windows reviewer | Git line-ending warning | Added `.gitattributes` (`eol=lf`), and the script normalises CRLF before matching. Re-verified from a fresh clone |

## Interpretation decisions flagged for human confirmation
- **A4 window reading.** "Previous Monday 00:00 through the following Monday 00:00" was read as the last *complete* week (run 10-13 → [10-05, 10-12)). The other possible reading, "Monday just gone to next Monday", would include future time, so it was rejected.
- **A1 naive timestamps** reject the whole run rather than skipping the one task. That's a fail-closed choice: no money moves on suspect data.

## Candidate verification — TO BE COMPLETED BY PRAVEEN (do not submit with blanks)
Recompute each expected value by hand from R1–R6, then tick.

| Check | Done | Notes |
|---|---|---|
| Window for run 2026-10-13 09:00Z = [10-05 00:00Z, 10-12 00:00Z) | ☐ | |
| TC05/06/07 UTC conversions (SAST +2, BST +1) | ☐ | |
| TC13 faulty actual = 50 (walk through the loop by hand) | ☐ | |
| Read `settlement_faulty.py` vs `settlement_fixed.py`: the only behavioural difference is DEF-001 | ☐ | |
| Ran `pytest --impl=faulty` and `--impl=fixed` personally on a fresh clone | ☐ | |
| Anything you changed, rejected or disagreed with (your own corrections) | ☐ | |
