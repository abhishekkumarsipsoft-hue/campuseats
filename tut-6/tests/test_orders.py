"""
CS543 A6 tests. Covers A4/A5 behaviour (no regressions, D4) plus the new
status codes, Problem Details, validation, and negotiation.
"""
import xml.etree.ElementTree as ET

import pytest

import app as appmod
import store
from payments_client import PaymentsRejected, PaymentsUnavailable

AUTH = {"Authorization": "Bearer test-token"}

VALID_ORDER = {
    "customer_id": "student-42",
    "address": "Hostel B, Room 214",
    "items": [{"name": "Masala Dosa", "price_cents": 8000, "qty": 2}],
}

TYPE_BASE = "https://campuseats.example/problems/"


def make_order(client, **headers):
    r = client.post("/orders", json=VALID_ORDER, headers={**AUTH, **headers})
    assert r.status_code == 201
    return r.get_json()["id"]


def assert_problem(resp, status, slug):
    assert resp.status_code == status
    assert resp.headers["Content-Type"] == "application/problem+json; charset=utf-8"
    body = resp.get_json()
    assert {"type", "title", "status", "detail"} <= set(body)
    assert body["status"] == status
    assert body["type"] == TYPE_BASE + slug
    return body


# ---------------------------------------------------------------- A: status codes
def test_create_order_201_with_location(client):
    r = client.post("/orders", json=VALID_ORDER, headers={**AUTH, "Idempotency-Key": "key-1"})
    assert r.status_code == 201
    body = r.get_json()
    assert r.headers["Location"] == f"/orders/{body['id']}"
    assert body["status"] == "placed" and body["total_cents"] == 16000
    assert body["address"] == "Hostel B, Room 214"
    assert "idempotency_key" not in body and "payment_txn_id" not in body


def test_unauthenticated_401(client):
    r = client.post("/orders", json=VALID_ORDER)
    assert_problem(r, 401, "unauthorized")


def test_unknown_id_404_order_not_found(client):
    assert_problem(client.get("/orders/nope"), 404, "order-not-found")


def test_unknown_route_is_problem_json_not_html(client):
    assert_problem(client.get("/nope"), 404, "not-found")


def test_wrong_method_405_problem_with_allow(client):
    r = client.put(f"/orders/{make_order(client)}")
    assert_problem(r, 405, "method-not-allowed")
    assert "GET" in r.headers["Allow"]


# ---------------------------------------------------------------- A4/A5 regressions (D4)
def test_idempotent_repeat_returns_original(client):
    h = {**AUTH, "Idempotency-Key": "key-2"}
    first = client.post("/orders", json=VALID_ORDER, headers=h)
    second = client.post("/orders", json=VALID_ORDER, headers=h)
    assert first.status_code == second.status_code == 201
    assert first.get_json()["id"] == second.get_json()["id"]
    assert len(store.orders) == 1


def test_conditional_get_304(client):
    oid = make_order(client)
    etag = client.get(f"/orders/{oid}").headers["ETag"]
    r = client.get(f"/orders/{oid}", headers={"If-None-Match": etag})
    assert r.status_code == 304 and r.data == b""


def test_stale_if_match_412(client):
    oid = make_order(client)
    r = client.post(f"/orders/{oid}/cancellation", json={}, headers={**AUTH, "If-Match": 'W/"stale"'})
    assert_problem(r, 412, "precondition-failed")


def test_if_match_with_current_etag_allows_the_write(client):
    oid = make_order(client)
    etag = client.get(f"/orders/{oid}").headers["ETag"]
    r = client.post(f"/orders/{oid}/cancellation", json={}, headers={**AUTH, "If-Match": etag})
    assert r.status_code == 202


# ---------------------------------------------------------------- B3 / C1 / C2: validation
def test_empty_cart_422_empty_cart(client):
    r = client.post("/orders", json=dict(VALID_ORDER, items=[]), headers=AUTH)
    body = assert_problem(r, 422, "empty-cart")
    assert body["errors"] == [{"field": "items", "message": "cart must contain at least one item"}]


def test_two_bad_fields_reported_at_once(client):
    bad = {"customer_id": "s", "address": "", "items": [{"name": "Dosa", "price_cents": 100, "qty": 0}]}
    body = assert_problem(client.post("/orders", json=bad, headers=AUTH), 422, "validation-error")
    fields = {e["field"] for e in body["errors"]}
    assert fields == {"address", "items[0].qty"}
    assert all(e["message"] for e in body["errors"])


def test_every_error_is_collected_not_just_the_first(client):
    bad = {"items": [{"name": "", "price_cents": -1, "qty": "2"}]}
    body = assert_problem(client.post("/orders", json=bad, headers=AUTH), 422, "validation-error")
    assert {e["field"] for e in body["errors"]} == {
        "customer_id", "address", "items[0].name", "items[0].price_cents", "items[0].qty",
    }


@pytest.mark.parametrize("field", ["qty", "price_cents"])
def test_booleans_are_not_integers(client, field):
    item = {"name": "x", "price_cents": 1, "qty": 1, field: True}
    r = client.post("/orders", json=dict(VALID_ORDER, items=[item]), headers=AUTH)
    assert_problem(r, 422, "validation-error")


def test_address_is_required(client):
    body = {k: v for k, v in VALID_ORDER.items() if k != "address"}
    r = client.post("/orders", json=body, headers=AUTH)
    assert [e["field"] for e in assert_problem(r, 422, "validation-error")["errors"]] == ["address"]


def test_invalid_work_is_not_done(client):
    client.post("/orders", json=dict(VALID_ORDER, items=[]), headers={**AUTH, "Idempotency-Key": "k9"})
    assert store.orders == {} and store.idempotency_index == {}


def test_item_unavailable_422(client):
    item = {"name": "Sold-Out Samosa", "price_cents": 500, "qty": 1}
    r = client.post("/orders", json=dict(VALID_ORDER, items=[item]), headers=AUTH)
    body = assert_problem(r, 422, "item-unavailable")
    assert body["errors"][0]["field"] == "items[0].name"


def test_malformed_json_400(client):
    r = client.post("/orders", data="{not json", content_type="application/json", headers=AUTH)
    assert_problem(r, 400, "malformed-json")


def test_json_but_not_an_object_400(client):
    assert_problem(client.post("/orders", json=[1, 2], headers=AUTH), 400, "malformed-json")


def test_body_that_is_not_json_400(client):
    r = client.post("/orders", data="customer_id=x", content_type="text/plain", headers=AUTH)
    assert_problem(r, 400, "malformed-json")


def test_list_filters_by_status(client):
    make_order(client)
    assert len(client.get("/orders?status=placed").get_json()) == 1
    assert client.get("/orders?status=delivered").get_json() == []


# ---------------------------------------------------------------- PATCH / illegal transitions
def test_patch_walks_the_lifecycle(client):
    oid = make_order(client)
    for status in ("preparing", "out_for_delivery", "delivered"):
        r = client.patch(f"/orders/{oid}", json={"status": status}, headers=AUTH)
        assert r.status_code == 200 and r.get_json()["status"] == status
        assert "ETag" in r.headers


def test_patch_skipping_a_step_is_illegal_transition(client):
    oid = make_order(client)
    r = client.patch(f"/orders/{oid}", json={"status": "delivered"}, headers=AUTH)
    body = assert_problem(r, 409, "illegal-transition")
    assert "'placed'" in body["detail"] and "'delivered'" in body["detail"]
    assert client.get(f"/orders/{oid}").get_json()["status"] == "placed"


def test_patch_cannot_cancel(client):
    oid = make_order(client)
    r = client.patch(f"/orders/{oid}", json={"status": "cancelled"}, headers=AUTH)
    assert "DELETE" in assert_problem(r, 409, "illegal-transition")["detail"]


def test_patch_with_unknown_status_is_422(client):
    oid = make_order(client)
    r = client.patch(f"/orders/{oid}", json={"status": "teleported"}, headers=AUTH)
    body = assert_problem(r, 422, "validation-error")
    assert [e["field"] for e in body["errors"]] == ["status"]


def test_patch_requires_auth_and_existing_order(client):
    oid = make_order(client)
    assert_problem(client.patch(f"/orders/{oid}", json={"status": "preparing"}), 401, "unauthorized")
    assert_problem(client.patch("/orders/nope", json={"status": "preparing"}, headers=AUTH), 404, "order-not-found")


# ---------------------------------------------------------------- DELETE / cancellation
def test_delete_cancels_with_204(client):
    oid = make_order(client)
    r = client.delete(f"/orders/{oid}", headers=AUTH)
    assert r.status_code == 204 and r.data == b""
    assert client.get(f"/orders/{oid}").get_json()["status"] == "cancelled"


def test_delete_twice_is_illegal_transition(client):
    oid = make_order(client)
    client.delete(f"/orders/{oid}", headers=AUTH)
    assert_problem(client.delete(f"/orders/{oid}", headers=AUTH), 409, "illegal-transition")


@pytest.mark.parametrize("status", ["out_for_delivery", "delivered"])
def test_delete_past_the_cancellable_window_is_illegal_transition(client, status):
    oid = make_order(client)
    store.orders[oid].status = status
    assert_problem(client.delete(f"/orders/{oid}", headers=AUTH), 409, "illegal-transition")


def test_cancellation_subresource_202(client):
    oid = make_order(client)
    r = client.post(f"/orders/{oid}/cancellation", json={"reason": "changed my mind"}, headers=AUTH)
    assert r.status_code == 202
    assert r.get_json()["refund_status"] == "refunded"
    assert_problem(client.post(f"/orders/{oid}/cancellation", headers=AUTH), 409, "illegal-transition")


def test_refund_declined_402_and_order_is_unchanged(client, monkeypatch):
    def declined(*a, **k):
        raise PaymentsRejected(402, '{"error":"card_declined","secret":"issuer-internal-id-77"}')
    monkeypatch.setattr(appmod, "request_refund", declined)
    oid = make_order(client)
    r = client.delete(f"/orders/{oid}", headers=AUTH)
    body = assert_problem(r, 402, "payment-declined")
    assert "issuer-internal-id-77" not in r.get_data(as_text=True)  # B4
    assert store.orders[oid].status == "placed"


def test_payments_down_503_with_retry_after_then_retry_works(client, monkeypatch):
    def down(*a, **k):
        raise PaymentsUnavailable("connection refused to http://10.0.0.5:9001")
    monkeypatch.setattr(appmod, "request_refund", down)
    oid = make_order(client)
    r = client.delete(f"/orders/{oid}", headers=AUTH)
    assert_problem(r, 503, "payments-unavailable")
    assert r.headers["Retry-After"] == "30"
    assert "10.0.0.5" not in r.get_data(as_text=True)
    assert store.orders[oid].status == "placed"          # not stuck in 'cancelling'

    monkeypatch.setattr(appmod, "request_refund", lambda *a, **k: {"status": "refunded"})
    assert client.delete(f"/orders/{oid}", headers=AUTH).status_code == 204


# ---------------------------------------------------------------- B4: no internals
def test_unexpected_exception_is_mapped_to_clean_500(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("psycopg2.OperationalError: password=hunter2 host=db.internal")
    monkeypatch.setattr(appmod, "request_refund", boom)
    oid = make_order(client)
    r = client.delete(f"/orders/{oid}", headers=AUTH)
    assert_problem(r, 500, "internal-error")
    text = r.get_data(as_text=True)
    assert "hunter2" not in text and "Traceback" not in text and "psycopg2" not in text
    assert store.orders[oid].status == "placed"


# ---------------------------------------------------------------- C3 / C4: negotiation, labels
def test_default_is_json(client):
    oid = make_order(client)
    r = client.get(f"/orders/{oid}")
    assert r.headers["Content-Type"] == "application/json; charset=utf-8"


def test_accept_xml_returns_xml(client):
    oid = make_order(client)
    r = client.get(f"/orders/{oid}", headers={"Accept": "application/xml"})
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/xml; charset=utf-8"
    root = ET.fromstring(r.data)
    assert root.tag == "order"
    assert root.findtext("id") == oid
    assert root.findtext("address") == "Hostel B, Room 214"
    assert root.find("items/item/name").text == "Masala Dosa"
    assert root.findtext("total_cents") == "16000"


def test_xml_list(client):
    make_order(client)
    root = ET.fromstring(client.get("/orders", headers={"Accept": "application/xml"}).data)
    assert root.tag == "orders" and len(root.findall("order")) == 1


def test_unacceptable_accept_406(client):
    r = client.get("/orders", headers={"Accept": "text/html"})
    assert_problem(r, 406, "not-acceptable")


@pytest.mark.parametrize(
    "accept,expected",
    [
        ("*/*", "application/json"),
        ("application/*", "application/json"),
        ("application/json", "application/json"),
        ("application/xml;q=0.9, application/json;q=0.5", "application/xml"),
        ("text/html, application/xml;q=0.8", "application/xml"),
        ("application/json;q=0, application/xml", "application/xml"),
    ],
)
def test_accept_q_values(client, accept, expected):
    r = client.get("/orders", headers={"Accept": accept})
    assert r.status_code == 200 and r.headers["Content-Type"].startswith(expected)


def test_json_explicitly_refused_and_nothing_else_acceptable_is_406(client):
    r = client.get("/orders", headers={"Accept": "application/json;q=0"})
    assert r.status_code == 406


def test_every_response_labels_its_body_with_charset(client):
    oid = make_order(client)
    responses = [
        client.get(f"/orders/{oid}"),
        client.get("/orders"),
        client.get("/orders/nope"),
        client.get("/nope"),
        client.post("/orders", json={}, headers=AUTH),
        client.post("/orders", json=VALID_ORDER),
        client.get("/orders", headers={"Accept": "text/html"}),
        client.get(f"/orders/{oid}", headers={"Accept": "application/xml"}),
    ]
    for r in responses:
        assert "charset=utf-8" in r.headers["Content-Type"], (r.status_code, r.headers["Content-Type"])


# ---------------------------------------------------------------- A4: 429 + Retry-After
def test_rate_limit_429_has_retry_after(client, monkeypatch):
    monkeypatch.setattr(appmod, "RATE_LIMIT", 3)
    codes = [client.get("/orders").status_code for _ in range(3)]
    assert codes == [200, 200, 200]
    r = client.get("/orders")
    assert_problem(r, 429, "rate-limit-exceeded")
    assert 1 <= int(r.headers["Retry-After"]) <= appmod.RATE_WINDOW_S
    assert r.headers["X-RateLimit-Remaining"] == "0"


# ---------------------------------------------------------------- A2: no 200 for failures
def test_no_failure_is_ever_a_200(client):
    """Spot-check: each of these is a failure and none may come back 2xx."""
    oid = make_order(client)
    failures = [
        client.post("/orders", json={}, headers=AUTH),
        client.post("/orders", json=VALID_ORDER),
        client.get("/orders/nope"),
        client.patch(f"/orders/{oid}", json={"status": "delivered"}, headers=AUTH),
        client.delete("/orders/nope", headers=AUTH),
    ]
    assert all(r.status_code >= 400 for r in failures)
    assert all("ok" not in (r.get_json() or {}) for r in failures)
