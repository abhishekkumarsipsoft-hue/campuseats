"""
CampusEats Orders service - CS543 Assignment 4/5.

Endpoints (see openapi.yaml for the full contract):
  POST   /orders                      create an order
  GET    /orders/{id}                 read a single order
  GET    /orders?status=placed        filtered list
  POST   /orders/{id}/cancellation    state-changing sub-resource
  OPTIONS /orders/{id}                supported methods
"""
import time

from flask import Flask, request, jsonify

from models import Order, Cancellation, NOT_CANCELLABLE_STATUSES, compute_etag
import store

from errors import problem
from payments_client import request_refund, PaymentsUnavailable, PaymentsRejected

app = Flask(__name__)


@app.before_request
def apply_method_override():
    override = request.headers.get("X-HTTP-Method-Override")
    if override:
        request.environ["REQUEST_METHOD"] = override.upper()


def check_auth():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer ") or len(header) <= len("Bearer "):
        return problem(401, "Unauthorized", "A valid Bearer token is required.")
    return None


RATE_LIMIT = 100
RATE_WINDOW_S = 60
_rate_state = {}


def check_rate_limit(client_id):
    now = time.time()
    window_start, count = _rate_state.get(client_id, (now, 0))

    if now - window_start > RATE_WINDOW_S:
        window_start, count = now, 0

    count += 1
    _rate_state[client_id] = (window_start, count)
    remaining = max(0, RATE_LIMIT - count)
    allowed = count <= RATE_LIMIT
    return allowed, remaining


@app.before_request
def enforce_rate_limit():
    client_id = request.headers.get("Authorization", request.remote_addr)
    allowed, remaining = check_rate_limit(client_id)
    request.environ["_rate_remaining"] = remaining
    if not allowed:
        resp = problem(429, "Too Many Requests", "Rate limit exceeded. Please slow down.")
        resp.headers["Retry-After"] = str(RATE_WINDOW_S)
        resp.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
        resp.headers["X-RateLimit-Remaining"] = "0"
        return resp


def check_accept():
    accept = request.headers.get("Accept", "*/*")
    if accept in ("*/*", "") or "application/json" in accept or "application/*" in accept:
        return None
    return problem(406, "Not Acceptable", "This endpoint only produces application/json.")


@app.before_request
def enforce_content_negotiation():
    error = check_accept()
    if error:
        return error


@app.after_request
def add_global_headers(resp):
    remaining = request.environ.get("_rate_remaining", RATE_LIMIT)
    resp.headers.setdefault("X-RateLimit-Limit", str(RATE_LIMIT))
    resp.headers.setdefault("X-RateLimit-Remaining", str(remaining))

    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, Idempotency-Key, "
        "If-Match, If-None-Match, X-HTTP-Method-Override"
    )

    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

    return resp


def validate_create_order(body):
    if not isinstance(body, dict):
        return "Request body must be a JSON object."
    if not isinstance(body.get("customer_id"), str) or not body["customer_id"].strip():
        return "customer_id is required and must be a non-empty string."
    items = body.get("items")
    if not isinstance(items, list) or len(items) == 0:
        return "items must be a non-empty array."
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            return f"items[{i}] must be an object."
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            return f"items[{i}].name is required."
        if not isinstance(item.get("price_cents"), int) or item["price_cents"] < 0:
            return f"items[{i}].price_cents must be a non-negative integer."
        if not isinstance(item.get("qty"), int) or item["qty"] < 1:
            return f"items[{i}].qty must be a positive integer."
    return None


@app.post("/orders")
def create_order():
    auth_error = check_auth()
    if auth_error:
        return auth_error

    body = request.get_json(silent=True)

    error = validate_create_order(body)
    if error:
        return problem(400, "Malformed Order", error)

    idem_key = request.headers.get("Idempotency-Key")

    if idem_key and idem_key in store.idempotency_index:
        existing_id = store.idempotency_index[idem_key]
        existing = store.orders[existing_id]
        resp = jsonify(existing.as_json())
        resp.status_code = 201
        resp.headers["Location"] = f"/orders/{existing.id}"
        return resp

    order = Order(body["customer_id"], body["items"], idempotency_key=idem_key)
    store.orders[order.id] = order
    if idem_key:
        store.idempotency_index[idem_key] = order.id

    resp = jsonify(order.as_json())
    resp.status_code = 201
    resp.headers["Location"] = f"/orders/{order.id}"
    return resp


@app.get("/orders/<order_id>")
def get_order(order_id):
    order = store.orders.get(order_id)
    if order is None:
        return problem(404, "Order Not Found", f"No order with id {order_id}.")

    body = order.as_json()
    etag = compute_etag(body)

    client_etag = request.headers.get("If-None-Match")
    if client_etag == etag:
        resp = app.response_class(status=304)
        resp.headers["ETag"] = etag
        resp.headers["Cache-Control"] = "private, must-revalidate"
        return resp

    resp = jsonify(body)
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = "private, must-revalidate"
    return resp, 200


@app.route("/orders/<order_id>", methods=["OPTIONS"])
def order_options(order_id):
    resp = app.response_class(status=204)
    resp.headers["Allow"] = "GET, OPTIONS"
    return resp


@app.get("/orders")
def list_orders():
    status = request.args.get("status")
    result = [o.as_json() for o in store.orders.values() if status is None or o.status == status]
    return jsonify(result), 200


@app.post("/orders/<order_id>/cancellation")
def create_cancellation(order_id):
    auth_error = check_auth()
    if auth_error:
        return auth_error

    order = store.orders.get(order_id)
    if order is None:
        return problem(404, "Order Not Found", f"No order with id {order_id}.")

    client_etag = request.headers.get("If-Match")
    if client_etag is not None:
        current_etag = compute_etag(order.as_json())
        if client_etag != current_etag:
            return problem(
                412,
                "Precondition Failed",
                "The order has changed since you last read it. Re-fetch and retry.",
            )

    if order.status == "cancelled":
        return problem(409, "Order Already Cancelled", "This order has already been cancelled.")

    if order.status in NOT_CANCELLABLE_STATUSES:
        return problem(
            422,
            "Cancellation Not Allowed",
            f"Orders in status '{order.status}' can no longer be cancelled.",
        )

    body = request.get_json(silent=True) or {}
    reason = body.get("reason")

    previous_status = order.status
    order.status = "cancelling"
    cancellation = Cancellation(order_id=order.id, reason=reason)
    store.cancellations[order.id] = cancellation

    idem_key = request.headers.get("Idempotency-Key", f"cancel-{order.id}")

    try:
        request_refund(order.id, order.total_cents, idempotency_key=idem_key)
    except PaymentsRejected as exc:
        order.status = previous_status
        cancellation.refund_status = "failed"
        return problem(422, "Refund Rejected", f"Payments service rejected the refund: {exc.body}")
    except PaymentsUnavailable:
        cancellation.refund_status = "failed_pending_retry"
        resp = jsonify(cancellation.as_json())
        resp.status_code = 202
        return resp
    else:
        order.status = "cancelled"
        cancellation.refund_status = "refunded"
        resp = jsonify(cancellation.as_json())
        resp.status_code = 202
        return resp


if __name__ == "__main__":
    app.run(port=8000, debug=False)