# intent.md — Why this problem?

> All scenarios, data and scores here are **synthetic or judgement-based**. I have no incident history for this
> fictional rewards service, and I'm not claiming any. Where I talk about likelihood, it's reasoning, not measurement.

## The flow
A fictional rewards service settles completed tasks every **Tuesday 09:00 UTC**. Each run covers the window
**[previous Monday 00:00 UTC, Monday 00:00 UTC)**, with the upper bound excluded. Each qualifying task earns **10 test credits**.
A `task_id` is paid **once**, and retries never create a second payout. A notification is sent **only after a successful payout**,
and a notification failure **never reverses** that payout.

## Problems considered
I scored each candidate failure from 1 to 5 on four criteria. Higher means more reason to work on it.
- **Impact (×3).** Harm to users' money and trust, and the clean-up cost.
- **Likelihood (×2).** How plausibly normal operations would trigger it.
- **Silence (×2).** How likely it is to go unnoticed. Silent failures do more damage before anyone reacts.
- **Fit (×1).** Can it be reproduced and fixed convincingly within a 6–8 hour budget?

| # | Failure | Impact | Likelihood | Silence | Fit | Weighted (/40) |
|---|---|---|---|---|---|---|
| **A** | **Retry after a partial failure double-pays.** A notification fails, the run is marked FAILED, the retry re-pays already-paid tasks | 5 | 4 | 4 | 5 | **36** |
| B | Inclusive upper cut-off (`<=` Monday 00:00), so a boundary task is paid in two weeks | 4 | 2 | 4 | 5 | 29 |
| D | Window calculated from actual execution time, so a late or re-run job leaves gaps or overlaps | 4 | 3 | 3 | 3 | 28 |
| C | Naive local timestamps treated as UTC (e.g. SAST +2), so a task lands in the wrong week or is missed | 3 | 3 | 4 | 4 | 27 |
| E | Notification sent before the payout is confirmed, or for a failed payout | 2 | 3 | 2 | 5 | 21 |

## Why A ranked first
- **It does the most harm.** It overpays, and it can also underpay: tasks after the failure point go unpaid until someone retries. Overpaid credits are hard to recover.
- **It's triggered by ordinary events.** No special data is needed. A transient notification error plus a standard retry is enough. That's why I rated likelihood higher than B, which needs a task at exactly Monday 00:00:00.
- **It's silent.** The retried run ends COMPLETED, and overpaid users rarely complain. Only reconciliation would find it.
- **It's a real root cause, not a typo.** It breaks three rules at once (R4, R5, R6), and the fix is a design change: an idempotency key, plus a separate outbox for notifications. That gives a meaningful regression suite, not a one-character test.
- **B, C and D aren't dropped.** Their scenarios are still covered as boundary and timezone cases (TC02–TC07, TC16), and mutation checks M6 and M7 show the suite would catch them.

## Who's affected (fictional)
- **Users earning credits.** They get duplicate credits and messages, or delayed credits when a run aborts.
- **Finance/operations.** They have to reconcile, recover overpayments, and manually re-run with confidence.
- **Support.** They field "I got two messages" and "my credits are missing" tickets.

## Evidence
- A reproduction against a synthetic faulty reference build: one notification failure plus one retry takes the ledger to **50 credits instead of 30** (`evidence/demo.txt`, TC13).
- Five automated cases fail on the faulty build and pass on the fixed build. A mutation check shows the suite also catches partial fixes.
- There's no production data or incident record. This is a reasoned risk, demonstrated in a fixture.

## Intended value
A release gate that makes double-payment on retry **impossible to ship unnoticed**. It also gives a documented business-rule set (R1–R6) and a design (idempotent payout + outbox) that a real implementation could adopt.

## Non-goals
- Testing or touching any live financial or notification system.
- Real database transactions, concurrency between parallel runs, or crash consistency. These are listed as gaps.
- Account lifecycle changes (closed or suspended users) and admin overrides.
- Fixing all five failures in depth. Only A is solved in depth; B and C are covered by test cases.
- Performance or volume testing.
