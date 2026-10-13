"""
CampusEats Orders service - CS543 Assignment 6 (built on A4/A5).

Endpoints (see openapi.yaml for the full contract):
  POST   /orders                      create an order            201
  GET    /orders/{id}                 read one order             200 / 304
  GET    /orders?status=placed        filtered list              200
  PATCH  /orders/{id}                 move status forward        200
  DELETE /orders/{id}                 cancel + refund            204
  POST   /orders/{id}/cancellation    cancel (sub-resource)      202
  OPTIONS /orders/{id}                supported methods

A6 principle: the status line IS the result. Every failure goes through
errors.problem(), so there is one error shape and no "200 + ok:false".
"""
import logging
import math
import os
import time
import uuid

from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import HTTPException

import store
from errors import problem
from models import (
    NOT_CANCELLABLE_STATUSES,
    TRANSITIONS,
    Cancellation,
    Order,
    compute_etag,
)
from negotiation import negotiate, to_xml
from payments_client import PaymentsRejected, PaymentsUnavailable, request_refund
from validation import validate_create_order, validate_patch_order

log = logging.getLogger("campuseats.orders")

app = Flask(__name__)

PAYMENTS_RETRY_AFTER_S = 30


# A5 A5: X-HTTP-Method-Override (unchanged from A5).
@app.before_request
def apply_method_override():
    override = request.headers.get("X-HTTP-Method-Override")
    if override:
        request.environ["REQUEST_METHOD"] = override.upper()


# Auth (A4 B3): header handling only - no real token verification.
def check_auth():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer ") or len(header) <= len("Bearer "):
        return problem("unauthorized", "A valid Bearer token is required.")
    return None


# Rate limiting (A4/A5). Limit and window can be set from the environment so
# the transcript can demonstrate a 429 without sending 100 requests.
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "100"))
RATE_WINDOW_S = int(os.environ.get("RATE_WINDOW_S", "60"))
_rate_state = {}


def check_rate_limit(client_id):
    now = time.time()
    window_start, count = _rate_state.get(client_id, (now, 0))
    if now - window_start > RATE_WINDOW_S:
        window_start, count = now, 0
    count += 1
    _rate_state[client_id] = (window_start, count)
    remaining = max(0, RATE_LIMIT - count)
    retry_after = max(1, math.ceil(window_start + RATE_WINDOW_S - now))
    return count <= RATE_LIMIT, remaining, retry_after


@app.before_request
def enforce_rate_limit():
    client_id = request.headers.get("Authorization", request.remote_addr)
    allowed, remaining, retry_after = check_rate_limit(client_id)
    g.rate_remaining = remaining
    if not allowed:
        return problem(
            "rate-limit-exceeded",
            f"Rate limit of {RATE_LIMIT} requests per {RATE_WINDOW_S}s exceeded. "
            f"Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after), "X-RateLimit-Remaining": "0"},
        )


# A6 C3: content negotiation. JSON by default, XML if asked, else 406.
@app.before_request
def enforce_content_negotiation():
    fmt = negotiate(request.headers.get("Accept"))
    if fmt is None:
        return problem(
            "not-acceptable",
            "This service can produce application/json or application/xml only.",
        )
    g.fmt = fmt


def respond(data, status=200, root="order"):
    """Serialise `data` in whichever format the client negotiated."""
    if g.get("fmt", "json") == "xml":
        return Response(
            to_xml(root, data), status=status, content_type="application/xml; charset=utf-8"
        )
    resp = jsonify(data)
    resp.status_code = status
    return resp


# A6 C4: label every body. Plus the A4/A5 global headers.
@app.after_request
def add_global_headers(resp):
    if resp.status_code in (204, 304):
        resp.headers.pop("Content-Type", None)  # no body, so no body label
    ct = resp.headers.get("Content-Type", "")
    if ct and "charset" not in ct.lower() and (
        ct.startswith("text/") or "json" in ct or "xml" in ct
    ):
        resp.headers["Content-Type"] = f"{ct}; charset=utf-8"

    remaining = g.get("rate_remaining", RATE_LIMIT)
    resp.headers.setdefault("X-RateLimit-Limit", str(RATE_LIMIT))
    resp.headers.setdefault("X-RateLimit-Remaining", str(remaining))

    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, Idempotency-Key, "
        "If-Match, If-None-Match, X-HTTP-Method-Override"
    )
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return resp


# A6 B1/B4: nothing but Problem Details ever reaches the client.
_HTTP_SLUGS = {400: "bad-request", 404: "not-found", 405: "method-not-allowed"}


@app.errorhandler(HTTPException)
def handle_http_exception(exc):
    """Flask/Werkzeug's own errors (unknown URL, wrong method...) are HTML by
    default. Route them through problem() so the shape never changes."""
    code = exc.code or 500
    slug = _HTTP_SLUGS.get(code, "bad-request" if code < 500 else "internal-error")
    headers = {}
    if code == 405 and getattr(exc, "valid_methods", None):
        headers["Allow"] = ", ".join(sorted(exc.valid_methods))
    detail = {
        404: "No such resource on this service.",
        405: "That method is not allowed on this resource.",
    }.get(code, "The request could not be processed." if code < 500 else "A server error occurred.")
    return problem(slug, detail, headers=headers, status=code)


@app.errorhandler(Exception)
def handle_unexpected(exc):
    """Last line of defence. Full detail + stack trace go to the server log
    under a reference id; the client only ever sees the id."""
    ref = uuid.uuid4().hex[:12]
    log.exception("Unhandled error ref=%s on %s %s", ref, request.method, request.path)
    return problem(
        "internal-error",
        f"Something went wrong on our side. Quote reference {ref} if you contact support.",
    )


# ---------------------------------------------------------------- helpers
def read_json_object():
    """Return (body, error_response); the body must be a JSON object."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return None, problem("malformed-json", "Request body must be a valid JSON object.")
    return body, None


def validation_failed(errors, slug="validation-error"):
    n = len(errors)
    return problem(
        slug,
        f"{n} field{'s' if n != 1 else ''} failed validation. See errors[].",
        errors=errors,
    )


def find_order(order_id):
    order = store.orders.get(order_id)
    if order is None:
        return None, problem("order-not-found", f"No order with id {order_id}.")
    return order, None


# ---------------------------------------------------------------- POST /orders
@app.post("/orders")
def create_order():
    auth_error = check_auth()
    if auth_error:
        return auth_error

    body, error = read_json_object()
    if error:
        return error

    # C2: validate everything first, collect every error, then act.
    errors = validate_create_order(body)
    if errors:
        slug = "empty-cart" if body.get("items") == [] else "validation-error"
        return validation_failed(errors, slug)

    unavailable = [
        {"field": f"items[{i}].name", "message": f"'{it['name']}' is currently unavailable"}
        for i, it in enumerate(body["items"])
        if it["name"] in store.UNAVAILABLE_ITEMS
    ]
    if unavailable:
        return validation_failed(unavailable, "item-unavailable")

    idem_key = request.headers.get("Idempotency-Key")
    if idem_key and idem_key in store.idempotency_index:
        existing = store.orders[store.idempotency_index[idem_key]]
        resp = respond(existing.as_json(), 201)
        resp.headers["Location"] = f"/orders/{existing.id}"
        return resp

    order = Order(body["customer_id"], body["address"], body["items"], idempotency_key=idem_key)
    store.orders[order.id] = order
    if idem_key:
        store.idempotency_index[idem_key] = order.id

    resp = respond(order.as_json(), 201)
    resp.headers["Location"] = f"/orders/{order.id}"
    return resp


# ---------------------------------------------------------------- GET /orders/{id}
@app.get("/orders/<order_id>")
def get_order(order_id):
    order, error = find_order(order_id)
    if error:
        return error

    etag = compute_etag(order.as_json())

    if request.headers.get("If-None-Match") == etag:
        resp = app.response_class(status=304)
        resp.headers["ETag"] = etag
        resp.headers["Cache-Control"] = "private, must-revalidate"
        return resp

    resp = respond(order.as_json(), 200)
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = "private, must-revalidate"
    return resp


@app.route("/orders/<order_id>", methods=["OPTIONS"])
def order_options(order_id):
    resp = app.response_class(status=204)
    resp.headers["Allow"] = "GET, PATCH, DELETE, OPTIONS"
    return resp


# ---------------------------------------------------------------- GET /orders
@app.get("/orders")
def list_orders():
    status = request.args.get("status")
    result = [o.as_json() for o in store.orders.values() if status is None or o.status == status]
    return respond(result, 200, root="orders")


# ---------------------------------------------------------------- PATCH /orders/{id}
@app.patch("/orders/<order_id>")
def update_order(order_id):
    auth_error = check_auth()
    if auth_error:
        return auth_error
    order, error = find_order(order_id)
    if error:
        return error
    body, error = read_json_object()
    if error:
        return error
    errors = validate_patch_order(body)
    if errors:
        return validation_failed(errors)

    new_status = body["status"]
    current = order.status
    if new_status not in TRANSITIONS.get(current, ()):
        hint = ""
        if new_status in ("cancelling", "cancelled"):
            hint = " To cancel, use DELETE /orders/{id} or POST /orders/{id}/cancellation."
        return problem(
            "illegal-transition",
            f"An order in status '{current}' cannot move to '{new_status}'.{hint}",
        )
    order.status = new_status

    resp = respond(order.as_json(), 200)
    resp.headers["ETag"] = compute_etag(order.as_json())
    return resp


# ---------------------------------------------------------------- cancellation
def cancel_order(order, reason=None):
    """Shared by DELETE /orders/{id} and POST /orders/{id}/cancellation.
    Returns (Cancellation, None) on success or (None, error_response).

    If the refund fails for ANY reason the order goes back to the status it
    had before - it never stays stuck in 'cancelling'."""
    if order.status == "cancelled":
        return None, problem("illegal-transition", "This order has already been cancelled.")
    if order.status in NOT_CANCELLABLE_STATUSES:
        return None, problem(
            "illegal-transition",
            f"Orders in status '{order.status}' can no longer be cancelled.",
        )

    previous_status = order.status
    order.status = "cancelling"
    idem_key = request.headers.get("Idempotency-Key", f"cancel-{order.id}")
    try:
        request_refund(order.id, order.total_cents, idempotency_key=idem_key)
    except PaymentsRejected as exc:
        order.status = previous_status
        # B4: the raw Payments body stays in our log, not in the response.
        log.warning("Payments rejected refund for %s: %s %s", order.id, exc.status_code, exc.body)
        return None, problem(
            "payment-declined", "The payment provider declined the refund. The order was not cancelled."
        )
    except PaymentsUnavailable as exc:
        order.status = previous_status
        log.error("Payments unreachable while refunding %s: %s", order.id, exc)
        return None, problem(
            "payments-unavailable",
            "The payment service is temporarily unavailable. The order was not cancelled; "
            "retrying the same request is safe.",
            headers={"Retry-After": str(PAYMENTS_RETRY_AFTER_S)},
        )
    except Exception:
        order.status = previous_status
        raise

    order.status = "cancelled"
    cancellation = Cancellation(order_id=order.id, reason=reason)
    cancellation.refund_status = "refunded"
    store.cancellations[order.id] = cancellation
    return cancellation, None


def check_if_match(order):
    client_etag = request.headers.get("If-Match")
    if client_etag is not None and client_etag != compute_etag(order.as_json()):
        return problem(
            "precondition-failed",
            "The order has changed since you last read it. Re-fetch and retry.",
        )
    return None


@app.post("/orders/<order_id>/cancellation")
def create_cancellation(order_id):
    auth_error = check_auth()
    if auth_error:
        return auth_error
    order, error = find_order(order_id)
    if error:
        return error
    precondition = check_if_match(order)
    if precondition:
        return precondition

    body = request.get_json(silent=True)
    reason = body.get("reason") if isinstance(body, dict) else None
    cancellation, error = cancel_order(order, reason)
    if error:
        return error
    return respond(cancellation.as_json(), 202, root="cancellation")


@app.delete("/orders/<order_id>")
def delete_order(order_id):
    auth_error = check_auth()
    if auth_error:
        return auth_error
    order, error = find_order(order_id)
    if error:
        return error
    _, error = cancel_order(order)
    if error:
        return error
    return app.response_class(status=204)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app.run(port=int(os.environ.get("PORT", "8000")), debug=False)
