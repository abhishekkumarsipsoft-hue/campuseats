"""
A6 B1/B2: one error shape everywhere, with a fixed type catalogue.

Every failure response is built by problem() - modelled on RFC 7807:
    type / title / status / detail   (+ errors[] for field-level failures)
Content-Type is application/problem+json; charset=utf-8.

The `type` slug is STABLE: clients may switch on it. Titles and details may
be reworded; slugs never change. Status is looked up from the catalogue so a
slug can never be sent with two different statuses.
"""
from flask import jsonify

TYPE_BASE = "https://campuseats.example/problems/"

# slug -> (status, title)
CATALOGUE = {
    # --- the five required by the brief (B2) ---
    "empty-cart":            (422, "Empty Cart"),
    "item-unavailable":      (422, "Item Unavailable"),
    "payment-declined":      (402, "Payment Declined"),
    "order-not-found":       (404, "Order Not Found"),
    "illegal-transition":    (409, "Illegal Transition"),
    # --- the rest of the failure space ---
    "validation-error":      (422, "Validation Failed"),
    "bad-request":           (400, "Bad Request"),
    "malformed-json":        (400, "Malformed JSON"),
    "unauthorized":          (401, "Unauthorized"),
    "not-found":             (404, "Resource Not Found"),
    "method-not-allowed":    (405, "Method Not Allowed"),
    "not-acceptable":        (406, "Not Acceptable"),
    "precondition-failed":   (412, "Precondition Failed"),
    "rate-limit-exceeded":   (429, "Too Many Requests"),
    "internal-error":        (500, "Internal Error"),
    "payments-unavailable":  (503, "Payments Unavailable"),
}


def problem(slug, detail, errors=None, headers=None, status=None):
    default_status, title = CATALOGUE[slug]
    status = status or default_status
    body = {
        "type": f"{TYPE_BASE}{slug}",
        "title": title,
        "status": status,
        "detail": detail,
    }
    if errors is not None:
        body["errors"] = errors

    resp = jsonify(body)
    resp.status_code = status
    resp.headers["Content-Type"] = "application/problem+json; charset=utf-8"
    for k, v in (headers or {}).items():
        resp.headers[k] = v
    return resp
