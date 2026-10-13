"""
Tiny stand-in for the Tutorial 4 Payments service, used only so this
service's outbound call has something real to hit for the curl transcript.
Not part of the Orders deliverable itself.

STUB_MODE=ok      (default) refunds succeed
STUB_MODE=decline every refund is refused with 402 (card declined)
STUB_PORT         port to listen on (default 9001)
"""
import os
from flask import Flask, request, jsonify

app = Flask(__name__)
seen_keys = {}
MODE = os.environ.get("STUB_MODE", "ok")


@app.post("/refunds")
def refund():
    if MODE == "decline":
        return jsonify({"error": "card_declined", "detail": "issuer refused the refund"}), 402
    key = request.headers.get("Idempotency-Key")
    if key and key in seen_keys:
        return jsonify(seen_keys[key]), 200
    body = request.get_json(silent=True) or {}
    result = {"refund_id": "rf_" + (key or "none"), "order_id": body.get("order_id"), "status": "refunded"}
    if key:
        seen_keys[key] = result
    return jsonify(result), 200


if __name__ == "__main__":
    app.run(port=int(os.environ.get("STUB_PORT", "9001")), debug=False)
