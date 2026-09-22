"""
D1/D2: the one real outbound HTTP call this service makes, to the
Payments service from Tutorial 4, hardened against a flaky network.

- Address comes from an environment variable, never a hard-coded URL.
- A short timeout so a hung Payments instance can't hang an Orders request.
- Retry with exponential backoff + jitter, but ONLY for failures that are
  safe to retry: connection errors, timeouts, and 5xx. A 4xx from
  Payments (e.g. 402 insufficient funds) means "don't bother retrying,
  this will keep failing" and is returned to the caller immediately.
- Any retried call carries an Idempotency-Key so a retried refund can
  never be double-processed on the Payments side.
"""
import os
import random
import time
import requests

PAYMENTS_URL = os.environ.get("PAYMENTS_SERVICE_URL", "http://localhost:9001")

MAX_ATTEMPTS = 4
BASE_DELAY_S = 0.2
TIMEOUT_S = 2.0


class PaymentsUnavailable(Exception):
    """Raised when Payments could not be reached after all retries."""


class PaymentsRejected(Exception):
    """Raised when Payments answered with a definitive 4xx - do not retry."""

    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Payments rejected request: {status_code} {body}")


def request_refund(order_id: str, amount_cents: int, idempotency_key: str) -> dict:
    """POST {PAYMENTS_URL}/refunds with retry/backoff/jitter. Returns the
    parsed JSON body on success."""
    url = f"{PAYMENTS_URL}/refunds"
    payload = {"order_id": order_id, "amount_cents": amount_cents}
    headers = {"Idempotency-Key": idempotency_key}

    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_S)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
        else:
            if resp.status_code < 300:
                return resp.json()
            if 400 <= resp.status_code < 500:
                # Not our problem to retry - the request is definitively bad.
                raise PaymentsRejected(resp.status_code, resp.text)
            # 5xx: treat like a transient failure and retry.
            last_exc = RuntimeError(f"Payments returned {resp.status_code}")

        if attempt < MAX_ATTEMPTS:
            backoff = BASE_DELAY_S * (2 ** (attempt - 1))
            jitter = random.uniform(0, backoff)
            time.sleep(backoff + jitter)

    raise PaymentsUnavailable(str(last_exc))
