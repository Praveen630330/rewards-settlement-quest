# Loom script (target 4:30, hard limit 5:00)

Use your own words. This is a timing guide, not something to read out.

| Time | Show on screen | Say (key points) |
|---|---|---|
| 0:00–0:30 | `intent.md` ranking table | The flow and rules in one sentence. I ranked five failures on impact, likelihood, silence and fit. These are judgement scores; there's no incident history. |
| 0:30–1:15 | Same table, then `docs/flow.md` faulty diagram | Why A ranked first: silent money loss triggered by routine events (a notification blip plus a standard retry), and it breaks R4, R5 and R6. B and C are still covered as test cases. |
| 1:15–2:15 | Terminal: `python demo.py` | Faulty: attempt 1 FAILED with 20 credits, retry gives 50, T1 and T2 paid twice. Fixed: 30 then 30, T2 notified once. Point at the root cause in `settlement_faulty.py`: notify inside the payout loop, and no idempotency key. |
| 2:15–3:15 | `pytest --impl=faulty` then `--impl=fixed`; CI run page | The same 20 tests: 8 fail on faulty ("expected 30, got 50"), 20 pass on fixed. CI has two jobs: `release-gate` must pass, `prove-regression` must fail on the faulty build. |
| 3:15–4:00 | `python scripts/mutation_check.py`; `docs/ai-log.md` C2/C3 | **The key verification and revision.** The first M4 mutant was equivalent and proved nothing, so I replaced it with notify-before-pay, which TC14 catches. M2 survives by design (defence in depth). Say what *you* checked or changed yourself. |
| 4:00–4:45 | `docs/release-checklist.md` decision; directive appendix F | GO to merge the fix in the reference build. NO-GO for production-like use until there's a DB unique constraint, a concurrency test, atomic payout and outbox, and monitoring. Remaining gaps. |
| 4:45–5:00 | — | AI use: Claude drafted the code and docs; I chose the scope and the failure, verified the expected values and own the decisions. Actual effort: X hours. |
