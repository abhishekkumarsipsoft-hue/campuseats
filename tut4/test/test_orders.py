import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import store
from app import app


@pytest.fixture(autouse=True)
def clean_store():
    store.reset()
    yield
    store.reset()


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    return app.test_client()


VALID_ORDER = {
    "customer_id": "student-42",
    "items": [{"name": "Masala Dosa", "price_cents": 8000, "qty": 2}],
}


def test_create_order_succeeds_with_right_code_and_location(client):
    resp = client.post("/orders", json=VALID_ORDER, headers={"Idempotency-Key": "key-1"})
    assert resp.status_code == 201
    assert resp.headers["Location"].startswith("/orders/")
    body = resp.get_json()
    assert body["status"] == "placed"
    assert body["total_cents"] == 16000
    # C2: internal fields must never leak into the representation
    assert "idempotency_key" not in body
    assert "payment_txn_id" not in body


def test_idempotent_repeat_returns_original(client):
    first = client.post("/orders", json=VALID_ORDER, headers={"Idempotency-Key": "key-2"})
    second = client.post("/orders", json=VALID_ORDER, headers={"Idempotency-Key": "key-2"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.get_json()["id"] == second.get_json()["id"]
    # only one order was actually created
    assert len(store.orders) == 1


def test_malformed_body_returns_400_with_problem_shape(client):
    resp = client.post("/orders", json={"customer_id": "student-42", "items": []})
    assert resp.status_code == 400
    body = resp.get_json()
    assert set(["type", "title", "status", "detail"]).issubset(body.keys())
    assert body["status"] == 400


def test_unknown_id_returns_404(client):
    resp = client.get("/orders/does-not-exist")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["status"] == 404
    assert body["title"] == "Order Not Found"
