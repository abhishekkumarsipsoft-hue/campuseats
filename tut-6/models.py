"""
Order model.

CS543 A4 - C2: the object we store (the "record") is not the same shape as
the object we publish (the "representation"). The record carries internal
bookkeeping that must never leak into a client-facing response.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone


def compute_etag(order_json: dict) -> str:
    """Weak ETag from the order's representation; changes whenever it does."""
    raw = json.dumps(order_json, sort_keys=True).encode("utf-8")
    return f'W/"{hashlib.sha256(raw).hexdigest()[:16]}"'


VALID_STATUSES = ("placed", "preparing", "out_for_delivery", "delivered", "cancelling", "cancelled")

# A6: the only moves PATCH /orders/{id} may make. Cancelling is deliberately
# NOT here - it needs a refund, so it goes through DELETE /orders/{id} or
# POST /orders/{id}/cancellation.
TRANSITIONS = {
    "placed": ("preparing",),
    "preparing": ("out_for_delivery",),
    "out_for_delivery": ("delivered",),
}

# Once an order has moved this far, the domain will not allow a cancellation.
NOT_CANCELLABLE_STATUSES = ("out_for_delivery", "delivered", "cancelled")


class Order:
    def __init__(self, customer_id, address, items, idempotency_key=None):
        self.id = str(uuid.uuid4())
        self.customer_id = customer_id
        self.address = address
        self.items = items  # list of {"name": str, "price_cents": int, "qty": int}
        self.total_cents = sum(i["price_cents"] * i["qty"] for i in items)
        self.status = "placed"
        self.created_at = datetime.now(timezone.utc).isoformat()

        # --- internal-only fields: part of the record, never the representation ---
        self.idempotency_key = idempotency_key
        self.payment_txn_id = None
        self.retry_count = 0

    def as_json(self):
        """The public representation. Deliberately narrower than the record."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "address": self.address,
            "items": self.items,
            "total_cents": self.total_cents,
            "status": self.status,
            "created_at": self.created_at,
        }


class Cancellation:
    """The sub-resource created at POST /orders/{id}/cancellation."""

    def __init__(self, order_id, reason=None):
        self.order_id = order_id
        self.reason = reason
        self.requested_at = datetime.now(timezone.utc).isoformat()
        self.refund_status = "pending"   # pending -> refunded

    def as_json(self):
        return {
            "order_id": self.order_id,
            "reason": self.reason,
            "requested_at": self.requested_at,
            "refund_status": self.refund_status,
        }
