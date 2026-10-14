"""Fictional weekly rewards settlement - assessment fixture (SYNTHETIC)."""
from __future__ import annotations

from . import settlement_faulty, settlement_fixed

IMPLEMENTATIONS = {
    "faulty": settlement_faulty.settle,
    "fixed": settlement_fixed.settle,
}


def get_settler(impl: str):
    try:
        return IMPLEMENTATIONS[impl]
    except KeyError:
        raise ValueError(f"unknown implementation {impl!r}; choose one of {sorted(IMPLEMENTATIONS)}") from None
