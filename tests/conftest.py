import os

import pytest

from rewards import get_settler
from rewards.selection import SettlementContext


def pytest_addoption(parser):
    parser.addoption(
        "--impl",
        default=os.environ.get("SETTLEMENT_IMPL", "fixed"),
        choices=["faulty", "fixed"],
        help="settlement implementation under test (default: fixed, or $SETTLEMENT_IMPL)",
    )


def pytest_report_header(config):
    return f"settlement implementation under test: {config.getoption('--impl')}"


@pytest.fixture
def settle(request):
    return get_settler(request.config.getoption("--impl"))


@pytest.fixture
def ctx():
    return SettlementContext()
