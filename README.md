# rewards-settlement-quest

A regression fixture for a **fictional** weekly rewards settlement. It guards against **DEF-001**: retrying a run after a
notification failure pays tasks twice. All data is synthetic.

Start with [`intent.md`](intent.md) for why this problem was chosen, then [`directive.md`](directive.md) for the rules, results and handoff.

## Quick start
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python demo.py                       # faulty vs fixed, side by side
python -m pytest --impl=faulty       # 5 failed, 12 passed (the regression cases fail)
python -m pytest --impl=fixed        # 17 passed
python scripts/mutation_check.py     # proves the suite catches partial fixes
```
`--impl` defaults to `fixed`, or to the `SETTLEMENT_IMPL` environment variable if set.

## Layout
| Path | Purpose |
|---|---|
| `src/rewards/settlement_faulty.py` | Reference faulty build (reproduces DEF-001) — do not fix |
| `src/rewards/settlement_fixed.py` | Corrected build: idempotent payout + notification outbox |
| `src/rewards/window.py`, `selection.py` | Window and eligibility rules shared by both builds |
| `tests/test_settlement.py` | 17 cases; `-m regression_a` selects the DEF-001 guards |
| `docs/` | Flow map, test cases and results, defect report, release checklist, AI log |
| `evidence/` | Captured local runs (pytest, JUnit, mutation, demo) |
| `.github/workflows/regression.yml` | CI: `release-gate` (must pass) + `prove-regression` (faulty must fail) |
