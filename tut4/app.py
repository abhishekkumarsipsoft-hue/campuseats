"""
CampusEats Orders service - CS543 Assignment 4.

Endpoints (see openapi.yaml for the full contract):
  POST   /orders                      create an order            (C3, C7)
  GET    /orders/{id}                 read a single order         (C3)
  GET    /orders?status=placed        filtered list                (C3)
  POST   /orders/{id}/cancellation    state-changing sub-resource (C3, D1/D2)
"""
from flask import Flask, request, jsonify

import store
from models import Order, Cancellation, NOT_CANCELLABLE_STATUSES
from errors import problem
from payments_client import request_refund, PaymentsUnavailable, PaymentsRejected

app = Flask(__name__)


# ---------------------------------------------------------------- C4
def validate_create_order(body):
    """Returns an error string, or None if the body is well-formed.
    This is the hand-written check that a WSDL's XML Schema used to
    give us for free (see NOTES.md answer 4)."""
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


# ---------------------------------------------------------------- C3 / C5 / C7 - create
@app.post("/orders")
def create_order():
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


# ---------------------------------------------------------------- C3 - read
@app.get("/orders/<order_id>")
def get_order(order_id):
    order = store.orders.get(order_id)
    if order is None:
        return problem(404, "Order Not Found", f"No order with id {order_id}.")
    return jsonify(order.as_json()), 200


# ---------------------------------------------------------------- C3 - filtered list
@app.get("/orders")
def list_orders():
    status = request.args.get("status")
    result = [o.as_json() for o in store.orders.values() if status is None or o.status == status]
    return jsonify(result), 200


# ---------------------------------------------------------------- C3 / D1 / D2 - state-changing sub-resource
@app.post("/orders/<order_id>/cancellation")
def create_cancellation(order_id):
    order = store.orders.get(order_id)
    if order is None:
        return problem(404, "Order Not Found", f"No order with id {order_id}.")

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
        # Payments gave a definitive "no" - this is a genuine domain problem,
        # not a network blip. Roll the order back and tell the caller why.
        order.status = previous_status
        cancellation.refund_status = "failed"
        return problem(422, "Refund Rejected", f"Payments service rejected the refund: {exc.body}")
    except PaymentsUnavailable:
        # D3: degrade rather than fail. The cancellation itself is still
        # accepted - the order stops moving through the kitchen/delivery
        # pipeline immediately - but the refund is queued for a retry.
        # See NOTES.md D3 for the reasoning.
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
