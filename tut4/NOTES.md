# CampusEats Orders Service — Assignment 4 Notes

**Team member(s):** [Your Name] — [Roll No]
*(fill in before submission; the assignment requires this on the first page)*

Service chosen: **Orders** (not Payments, per the assignment rules).

---

## A2 — Operations as I'd have written them for SOAP (Assignment 3 style)

Assignment 3 modelled a single external SOAP partner (SecurePay's
`ProcessRefund` operation — `types` → `message` → `portType` →
`binding` → `service`/`port`, one operation, credentials in the
`soap:Header`). Applying that same shape to Orders as a whole, before
any REST redesign, gives:

- `createOrder(customerId, items[]) -> Order`
- `getOrder(orderId) -> Order`
- `listOrdersByStatus(status) -> Order[]`
- `cancelOrder(orderId, reason) -> CancellationResult`
- `updateOrderStatus(orderId, newStatus) -> Order`

## A3 — Finding the nouns

| SOAP-style verb              | Durable thing it creates/changes | Plural noun    |
|---|---|---|
| createOrder                  | a new order record                 | **orders**       |
| getOrder                     | (reads) an order                   | **orders**       |
| listOrdersByStatus           | (reads) a set of orders            | **orders**       |
| cancelOrder                  | a cancellation event on an order   | **cancellations** |
| updateOrderStatus            | folded into the resource itself — status is a *field* of an order, not a separate thing worth its own endpoint in this service | (n/a — represented as `status` on `Order`) |

## A4 — Resource table

| Method | URL | What it does | Success code | Failure codes |
|---|---|---|---|---|
| `POST` | `/orders` | Create an order from a customer id and a list of items. Supports `Idempotency-Key`. | `201 Created` (+ `Location`) | `400` malformed body |
| `GET` | `/orders/{orderId}` | Read a single order. | `200 OK` | `404` not found |
| `GET` | `/orders?status={status}` | List orders, optionally filtered by status (query string). | `200 OK` | — |
| `POST` | `/orders/{orderId}/cancellation` | **Sub-resource.** Create a cancellation for an order; triggers a refund call to Payments. | `202 Accepted` | `404` not found, `409` already cancelled, `422` past cancellable window / Payments rejected the refund |

(Minimum of four rows met; `/orders/{orderId}/cancellation` is the required sub-resource row.)

## A5 — The hard choice

`updateOrderStatus` was the operation that mapped least comfortably onto a resource. As a SOAP-style verb it looks like it deserves its own endpoint — but a status is not a durable *thing* a client creates; it's a field that changes as a side effect of other real-world events (the kitchen starts cooking, a rider picks up the order, Payments confirms a refund). Modelling `PATCH /orders/{id}/status` would have let a client set an order to *any* status directly, which is not a power we want to hand out — a client should never be able to jump an order straight to `delivered`. I resolved this by keeping `status` as a read-only field on `Order` that only the service's own internal transitions and the one sub-resource I did expose (`/orders/{id}/cancellation`) are allowed to change. I rejected a generic status-update endpoint because it would have turned an internal state machine into a public, unconstrained API.

## D3 — Fallback when Payments is unreachable

When the cancellation endpoint's call to Payments fails after retries (`PaymentsUnavailable`), the service **degrades rather than fails**: the cancellation is still accepted (`202`), the order's kitchen/delivery pipeline stops immediately, and the cancellation record is marked `refund_status: failed_pending_retry` for a background job to retry later. Failing the whole cancellation instead — telling the student "no, you're still getting this food" — would have been the wrong call: the customer's *right to cancel* and the *refund* are two different guarantees, and only one of them depends on Payments being up. Refusing to let someone cancel an order just because an unrelated downstream system is slow would punish the customer for our infrastructure problem. The one case where we do *not* degrade is `PaymentsRejected` (a definitive 4xx, e.g. no such payment on file) — that's a genuine business answer, not a network problem, so the cancellation itself is rolled back and reported as `422`.

---

## Answers

### 1. WSDL line count vs. openapi.yaml line count

My Assignment 3 `partner.wsdl` (SecurePay, **one** operation — `ProcessRefund`) is **92 lines**. `openapi.yaml` here (Orders, **four** operations plus every request/response schema and every documented failure) is **232 lines**. Read as raw totals that looks like OpenAPI is the more verbose format — but it's covering four times the ground. Normalised per operation, the WSDL costs about 92 lines/operation and the OpenAPI file costs about 58 lines/operation (232 ÷ 4), so OpenAPI is actually the *more compact* format once the comparison is fair.

The difference isn't really "who is more verbose" — it's *where the words go*. `partner.wsdl` spends real estate on `<types>` (hand-written XSD complex types), a `<message>`/`<part>` pairing for input, output, *and* the fault, a `<portType>` restating the operation's signature a second time, and a `<binding>` that re-declares the SOAP transport, style and `soapAction` for that one operation. `openapi.yaml` never repeats a shape: `$ref` to `components.schemas` means each schema (`Order`, `OrderItem`, `Problem`, …) is written exactly once no matter how many operations reuse it, and the HTTP method plus status code *is* the binding, so there's no separate section restating "how do I physically call this."

Two things the WSDL declared that OpenAPI does not need:
- **A `<binding>` per operation.** WSDL treats "how do I physically call this" as something to declare per-operation (transport, style, `soapAction` header). OpenAPI declares it once, implicitly, by using HTTP itself — `POST /orders` *is* the binding.
- **A `<portType>`/`<service>`/`<port>` triad.** WSDL separates the abstract operation signature from the concrete address where you reach it (and from the `<service>` wrapper a UDDI-style registry would publish). OpenAPI folds "where do I call this" into one `servers:` block at the top of the whole document, shared by every operation instead of repeated per operation.

### 2. A `soap:Fault` vs. its REST replacement

My Assignment 3 `soap-fault.xml`, from SecurePay's `ProcessRefund` operation, looked like this:

```xml
<soap:Fault>
  <faultcode>soap:Client</faultcode>
  <faultstring>Refund declined: original transaction already fully refunded</faultstring>
  <detail>
    <tns:RefundFaultDetail>
      <tns:gatewayErrorCode>card_declined</tns:gatewayErrorCode>
      <tns:orderReference>ORD-c4ed4779</tns:orderReference>
    </tns:RefundFaultDetail>
  </detail>
</soap:Fault>
```

`payments_client.py` (this assignment) catches exactly this class of
failure as `PaymentsRejected`, and `app.py`'s cancellation endpoint
turns it into an HTTP `422` carrying this problem body:

```json
{
  "type": "https://campuseats.example/problems/refund-rejected",
  "title": "Refund Rejected",
  "status": 422,
  "detail": "Payments service rejected the refund: card_declined"
}
```

Per the Assignment 3 binding I wrote in `integration.pdf`, that `soap:Fault` was carried inside an HTTP `200 OK` — SOAP treats the transport as a dumb envelope-carrier and puts *all* application meaning inside the XML body, whatever the HTTP status line says. That's a real problem for anything sitting between client and server: a caching proxy, a load balancer doing health checks, a monitoring tool counting error rates — none of them parse SOAP XML, so a `200` with a fault buried inside looks, to every piece of network infrastructure, identical to success. REST's `422` puts the meaning on the one layer every intermediary already understands, and — per the Assignment 3 "Fault mapping" section — SecurePay's own vocabulary (`card_declined`, `gatewayErrorCode`) never reaches the student; it's translated into CampusEats's one `problem()` shape at the boundary.

### 3. UDDI's publish / find / bind

- **Publish** — survives, but informally: instead of registering a WSDL in a UDDI registry, I "publish" by committing `openapi.yaml` to the shared repo — the same move Assignment 3 used for SecurePay, where "publish" was a one-row catalogue entry (business, service, endpoint, WSDL pointer) rather than a live registry.
- **Find** — survives, downgraded: instead of a UDDI `find_service` query by business/tModel, another team finds this service by reading the repo, or by an API gateway's own directory of registered `openapi.yaml` files — again, the same catalogue-row pattern as Assignment 3's Discovery section, just for a service we own instead of one we consume.
- **Bind** — mostly disappears as a distinct step. UDDI's `bind` resolved an abstract service description to a concrete, callable endpoint at runtime. In this setup, "bind" collapses into just reading `servers:` in the YAML (or, in D1/D2, reading `PAYMENTS_SERVICE_URL` from the environment) — there is no separate runtime resolution step because the URL *is* the contract.

What took over the job: a version-controlled file (`openapi.yaml`) in a repository, plus an environment variable for the one place where the address genuinely needs to vary between environments. Git history and code review replaced the registry's job of being the trustworthy source of "what's out there and where."

### 4. What replaced the XML Schema

`validate_create_order()` in `app.py` is the function that now carries the responsibility my Assignment 3 XML Schema used to carry for free — every field's type, presence, and basic shape (non-empty `customer_id`, a non-empty `items` array, each item's `price_cents` a non-negative int, `qty` a positive int) is checked there, by hand, before any field is touched.

One failure that would get through if I hadn't written it: a client sending `"price_cents": "eight thousand"` (a string instead of an integer) or `"qty": -1`. Without `validate_create_order()`, `sum(i["price_cents"] * i["qty"] for i in items)` in `models.py` would either throw an unhandled `TypeError` deep inside order construction (leaking a stack trace instead of a clean `400`), or — worse, with `qty: -1` — silently compute a *negative* order total that would then get sent to Payments as a real monetary amount.

### 5. Where I'd still choose SOAP/WSDL over REST

I'd choose the SOAP stack for exactly the edge Assignment 3 integrated: **the SecurePay payment gateway**, an external partner CampusEats does not control, specifically because of *WS-Security* and the strict, machine-checked contract WSDL/XSD gives you. The guarantee I'd be buying is: the message itself (not just the transport) is signed and can carry a verifiable audit trail end-to-end across untrusted intermediaries, and the request/response shape is enforced by schema validation *before* either side's business logic ever runs, with zero room for a "close enough" JSON body to slip through. That guarantee matters more than developer convenience in a context where the two parties don't share a deploy pipeline, can't agree to update client and server together, and where a regulator may eventually ask for a paper trail of exactly what was signed and when. Everywhere else in CampusEats — services we build and deploy ourselves, on a shared repo, on a release cycle we control — I'd stick with REST, because the coordination cost SOAP is designed to solve doesn't exist between our own services.
