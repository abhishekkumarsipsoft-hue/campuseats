"""
In-process storage for the Orders service.

C1 (A4): storage is plain dictionaries. No other CampusEats service may
import this module directly - they only reach Orders data via the HTTP API.
"""
orders = {}             # order_id -> Order
cancellations = {}      # order_id -> Cancellation
idempotency_index = {}  # idempotency_key -> order_id  (A4 C7)

# A6 B2 (item-unavailable): stand-in for the Catalogue service. Any order
# line naming one of these is refused. Real lookup would be an HTTP call.
UNAVAILABLE_ITEMS = {"Sold-Out Samosa"}


def reset():
    """Test helper - wipe all state between tests."""
    orders.clear()
    cancellations.clear()
    idempotency_index.clear()
