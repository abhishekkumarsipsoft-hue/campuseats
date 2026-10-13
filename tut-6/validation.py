"""
A6 C1/C2: validate first, collect EVERY problem, then act.

Each validator returns a list of {"field": ..., "message": ...} dicts
(empty list = valid). The caller turns a non-empty list into one 422.
"""
from models import VALID_STATUSES


def _is_int(v):
    # bool is a subclass of int in Python: True must not pass as 1.
    return isinstance(v, int) and not isinstance(v, bool)


def _err(field, message):
    return {"field": field, "message": message}


def validate_create_order(body):
    """POST /orders body. Returns a list of errors (empty = valid)."""
    errors = []

    if not isinstance(body.get("customer_id"), str) or not body["customer_id"].strip():
        errors.append(_err("customer_id", "is required and must be a non-empty string"))

    if not isinstance(body.get("address"), str) or not body["address"].strip():
        errors.append(_err("address", "is required and must be a non-empty string"))

    items = body.get("items")
    if items is None:
        errors.append(_err("items", "is required"))
    elif not isinstance(items, list):
        errors.append(_err("items", "must be an array"))
    elif len(items) == 0:
        errors.append(_err("items", "cart must contain at least one item"))
    else:
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(_err(f"items[{i}]", "must be an object"))
                continue
            if not isinstance(item.get("name"), str) or not item["name"].strip():
                errors.append(_err(f"items[{i}].name", "is required and must be a non-empty string"))
            if not _is_int(item.get("price_cents")) or item["price_cents"] < 0:
                errors.append(_err(f"items[{i}].price_cents", "must be an integer >= 0"))
            if not _is_int(item.get("qty")) or item["qty"] < 1:
                errors.append(_err(f"items[{i}].qty", "must be an integer >= 1"))
    return errors


def validate_patch_order(body):
    """PATCH /orders/{id}: `status` is required and must be a known status."""
    errors = []
    status = body.get("status")
    if status is None:
        errors.append(_err("status", "is required"))
    elif status not in VALID_STATUSES:
        errors.append(_err("status", f"must be one of: {', '.join(VALID_STATUSES)}"))
    return errors
