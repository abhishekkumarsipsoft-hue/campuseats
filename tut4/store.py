"""
In-process storage for the Orders service.

C1: storage is a plain dictionary. No other CampusEats service may
import this module directly - they only ever reach Orders data through
the HTTP API in app.py.
"""

orders = {}            # order_id -> Order
cancellations = {}      # order_id -> Cancellation
idempotency_index = {}  # idempotency_key -> order_id  (C7)


def reset():
    """Test helper - wipe all state between tests."""
    orders.clear()
    cancellations.clear()
    idempotency_index.clear()
