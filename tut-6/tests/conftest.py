import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import app as appmod
import store


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    store.reset()
    appmod._rate_state.clear()
    monkeypatch.setattr(appmod, "RATE_LIMIT", 1000)
    # By default the Payments call succeeds instantly; tests that care override it.
    monkeypatch.setattr(appmod, "request_refund", lambda *a, **k: {"status": "refunded"})
    yield
    store.reset()
    appmod._rate_state.clear()


@pytest.fixture()
def client():
    appmod.app.config["TESTING"] = True
    return appmod.app.test_client()
