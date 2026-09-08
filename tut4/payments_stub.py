"""
Tiny stand-in for the Tutorial 4 Payments service, used only so this
service's outbound call to Payments has something real to hit for the
curl transcript. Not part of the Orders deliverable itself.
"""
from flask import Flask, request, jsonify

app = Flask(__name__)
seen_keys = {}


@app.post("/refunds")
def refund():
    key = request.headers.get("Idempotency-Key")
    if key and key in seen_keys:
        return jsonify(seen_keys[key]), 200
    body = request.get_json(silent=True) or {}
    result = {"refund_id": "rf_" + (key or "none"), "order_id": body.get("order_id"), "status": "refunded"}
    if key:
        seen_keys[key] = result
    return jsonify(result), 200


if __name__ == "__main__":
    app.run(port=9001, debug=False)
