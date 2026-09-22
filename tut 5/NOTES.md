# CampusEats Orders Service — Assignment 5 Notes
## HTTP Methods & Headers

**Team ID:** [FILL IN]

**Team members:**
| Name | Roll No |
|---|---|
| Binamra Rana | 20251651033 |
| Abhishek Kumar | 20251651005 |
| Navendu Kumar Pandey | 20251651062 |
| Yatindra Kumar Yunish | 20251651106 |
| Shruti Singh | 20251651087 |

Service audited: **Orders** (same service as Assignment 4).

---

## A1 — CampusEats Method Map

| Action | Method | URL |
|---|---|---|
| Create an order | `POST` | `/orders` |
| Read a single order | `GET` | `/orders/{orderId}` |
| List / filter orders by status | `GET` | `/orders?status={status}` |
| Cancel an order (non-CRUD action) | `POST` | `/orders/{orderId}/cancellation` |
| Discover supported methods on an order | `OPTIONS` | `/orders/{orderId}` |

No verb leaked into a URL — the one non-CRUD action (`cancel`) was already modelled in
Assignment 4 as `POST /orders/{orderId}/cancellation`, a sub-resource, not
`POST /cancelOrder`. Verified against the brief: every remaining verb (`browseMenu`,
`makePayment`, `updateOrderStatus`, `trackDelivery`) belongs to a different service
(Catalogue, Payments, Delivery) and is out of scope for the Orders audit.

## A2 — Non-CRUD actions

`cancelOrder` was the only non-CRUD action in scope for Orders. It is modelled as
`POST /orders/{orderId}/cancellation` — a new sub-resource (a "cancellation record")
is created under the order, rather than exposing a bare RPC-style verb endpoint.

## A3 — Safe & Idempotent audit

| Endpoint | Safe? | Idempotent? | Why |
|---|---|---|---|
| `POST /orders` | No | Yes | Creates a new order, but a repeated request with the same `Idempotency-Key` returns the original order instead of creating a duplicate. |
| `GET /orders/{orderId}` | Yes | Yes | Read-only; never changes state. |
| `GET /orders?status=` | Yes | Yes | Read-only filtered list. |
| `POST /orders/{orderId}/cancellation` | No | Made retry-safe (see below) | Changes order state and triggers a refund call to Payments. |
| `OPTIONS /orders/{orderId}` | Yes | Yes | Only reports supported methods; changes nothing. |

No `GET` endpoint ever mutates state — confirmed by code review of `app.py`: both
`get_order` and `list_orders` only read from `store.orders`.

`POST /orders/{orderId}/cancellation` is **not naturally idempotent** (calling it twice
could trigger two refund attempts). We made it retry-safe using an `Idempotency-Key`
header (falling back to a deterministic `cancel-{order_id}` key if the client doesn't
supply one), exactly the same mechanism used for order creation in Assignment 4 (C7).

## A5 — OPTIONS + Allow, and override

`OPTIONS /orders/{orderId}` returns `204 No Content` with an `Allow: GET, OPTIONS`
header, so a client can discover what it may do on that resource before trying.

For constrained clients that cannot issue `PUT`/`DELETE` directly, the service accepts
`X-HTTP-Method-Override` as a documented fallback: if present, the header's value
overrides the incoming request's method before routing. This is implemented globally
in a `before_request` hook, not per-endpoint.

## A6 — One full exchange

**Request** (HTTP/1.1):
```
POST /orders HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Authorization: Bearer test-token-123
Idempotency-Key: key-abc-1

{"customer_id":"student-42","items":[{"name":"Masala Dosa","price_cents":8000,"qty":2}]}
```

**Response:**
```
HTTP/1.1 201 CREATED
Content-Type: application/json
Location: /orders/9a4103a2-6129-41c8-9610-cf842e38e2ce
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
Access-Control-Allow-Origin: *
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=63072000; includeSubDomains

{"created_at":"2026-09-22T16:31:11.085224+00:00","customer_id":"student-42","id":"9a4103a2-6129-41c8-9610-cf842e38e2ce","items":[{"name":"Masala Dosa","price_cents":8000,"qty":2}],"status":"placed","total_cents":16000}
```
(Full transcript with all headers in `curl-transcript.txt`, entry #1. Request line
declares `HTTP/1.1`.)

---

## D2 — Headers table

| Endpoint | Request headers it needs | Response headers it sets |
|---|---|---|
| `POST /orders` | `Content-Type`, `Authorization`, `Idempotency-Key` (optional), `Accept` | `Location`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Access-Control-Allow-*`, `X-Content-Type-Options`, `Strict-Transport-Security` |
| `GET /orders/{id}` | `If-None-Match` (optional), `Accept` | `ETag`, `Cache-Control`, `X-RateLimit-*`, CORS + security headers |
| `GET /orders?status=` | `Accept` | `X-RateLimit-*`, CORS + security headers |
| `POST /orders/{id}/cancellation` | `Content-Type`, `Authorization`, `Idempotency-Key` (optional), `If-Match` (optional) | `X-RateLimit-*`, CORS + security headers |
| `OPTIONS /orders/{id}` | — | `Allow`, CORS + security headers |

---

## C4 — The safe-retry plan

| Endpoint | Risk if retried blindly | Mechanism used | Why |
|---|---|---|---|
| `POST /orders` | Duplicate order, double charge | `Idempotency-Key` | Not safe, but made idempotent — repeat with the same key returns the original order. |
| `GET /orders/{id}` | None | `If-None-Match` | Already safe + idempotent; ETag support avoids re-sending an unchanged body. |
| `GET /orders?status=` | None | — (inherently safe) | Read-only; no mechanism needed. |
| `POST /orders/{id}/cancellation` | Double refund, stale-data overwrite | `Idempotency-Key` **and** `If-Match` | Not safe/idempotent by default; the key prevents duplicate refunds on retry, and `If-Match` prevents two clients from cancelling based on stale reads of the same order. |

This follows directly from the A3 split: the two `GET` endpoints are already safe and
idempotent, so they only need a caching mechanism (`If-None-Match`), not a
retry-safety mechanism. The two `POST` endpoints are neither safe nor naturally
idempotent, so each needs an explicit mechanism to make retries harmless.

---

## Answers

### 1. Three endpoints — method, success status, most important response header

- **`POST /orders`** — `201 Created` — the header that matters most is **`Location`**,
  because it tells the client exactly where the new order now lives, which it needs
  for every subsequent `GET`/cancellation call.
- **`GET /orders/{id}`** — `200 OK` — the header that matters most is **`ETag`**,
  because it's what makes every future conditional request (`If-None-Match`) possible;
  without it caching has nothing to compare against.
- **`POST /orders/{id}/cancellation`** — `202 Accepted` — the header that matters most
  is **`X-RateLimit-Remaining`**, since this is the one write endpoint a client might
  hammer on retry, and this header is what tells it how much budget is left before a
  `429` would kick in.

### 2. Safe / idempotent — which endpoint is neither, and how was it made retry-safe

Safe: `GET /orders/{id}`, `GET /orders?status=`, `OPTIONS /orders/{id}`.
Idempotent: those three, plus `POST /orders` (via `Idempotency-Key`).

Neither safe nor naturally idempotent: **`POST /orders/{id}/cancellation`** — it
changes order state and can trigger a real refund. It was made retry-safe with an
`Idempotency-Key` (any retry using the same key returns the already-recorded result
instead of firing a second refund) combined with `If-Match` (rejects the write outright
with `412` if the order changed since the client last read it, so a stale retry can't
silently clobber a newer state).

### 3. One ETag, the 304, and the 412 — what each saves/prevents

From `curl-transcript.txt`:
- ETag returned by `GET /orders/9a4103a2-...`: `ETag: W/"38b5eb7984c8d31a"`
- Request that returns `304`: the same `GET` repeated with
  `If-None-Match: W/"38b5eb7984c8d31a"` → `304 Not Modified`, empty body.
  **Saves bandwidth** — the client already has the current representation, so no body
  is re-sent.
- Write that returns `412`: `POST /orders/9a4103a2-.../cancellation` with
  `If-Match: W/"wrong-etag-value"` → `412 Precondition Failed`.
  **Prevents a lost update** — the write is rejected because the client's assumed
  version of the order doesn't match what the server actually has, so it can't
  overwrite a state it never saw.

### 4. 422 vs 400 — the exact requests and the difference

- **`400`** is triggered by a **malformed request**: 
  `POST /orders` with `{"customer_id": "student-42", "items": []}` → `400 Malformed
  Order` — the request body itself doesn't satisfy the schema (empty `items` array).
- **`422`** is triggered by a **well-formed request that the domain refuses**: 
  `POST /orders/{id}/cancellation` on an order whose status is already
  `out_for_delivery`/`delivered`/`cancelled` → `422 Cancellation Not Allowed` — the
  request is syntactically and structurally valid, but the business rules of the
  domain don't allow it right now.

The difference: `400` means "I can't even understand/accept this request as sent";
`422` means "I understood it perfectly, but the current state of the world says no."

### 5. Browser blocked despite a server 200 — who blocked it, which header fixes it

The **browser itself** blocked it — the CORS check happens client-side, after the
response has already arrived with `200`, so the server log correctly shows a
successful `200` even though the page never got to read the response. The fix is the
**`Access-Control-Allow-Origin`** response header (this service sets it to `*` in
`add_global_headers`), which tells the browser the response is allowed to be shared
with a page from a different origin. For a preflighted request, the browser also needs
the `OPTIONS` response to declare `Access-Control-Allow-Methods` /
`Access-Control-Allow-Headers` before the real request is even sent.

### 6. Cache-Control: cacheable vs no-store

- **Cacheable** — `GET /orders/{id}` uses `Cache-Control: private, must-revalidate`
  plus an `ETag`. It's cacheable (per-client) because the representation is stable
  between changes, and `must-revalidate` forces a conditional check rather than
  serving something stale, which keeps it safe.
- **`no-store`** — the failure responses (`400`, `401`, `404`, `409`, `412`, `422`)
  should never be cached, since they describe a specific request at a specific moment
  (a bad token, a stale ETag) that says nothing about future requests to the same URL;
  caching them could make a client believe an error is permanent when it isn't.

### 7. GET search endpoint — when would POST be the right choice, and what's given up

`GET /orders?status=` stays a `GET` because the filter is a small string. `POST` would
become the right choice if the search criteria grew large or complex enough that it no
longer fits comfortably in a query string (e.g. searching orders by a list of item
names, a date range, and multiple statuses at once) — at that point a JSON request
body is cleaner than an enormous query string, and some proxies/servers cap URL length.

What's given up by switching to `POST`: the request stops being **safe and cacheable**.
A browser or intermediary can no longer cache the result by URL, can't prefetch it, and
the request can't be bookmarked, shared as a link, or safely retried by infrastructure
that assumes only `GET`s are read-only.

### 8. Location on 201 vs on a 3xx

- On a **`201 Created`** (our `POST /orders`), `Location` points to the **newly
  created resource** — the URL of the order that now exists, e.g.
  `/orders/9a4103a2-6129-41c8-9610-cf842e38e2ce`.
- On a **`3xx` redirect**, `Location` points to **where the client should go instead**
  to get the resource it originally asked for — the target of the redirect, not
  something new that was just created.
