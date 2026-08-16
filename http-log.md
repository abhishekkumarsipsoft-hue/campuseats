# HTTP Log

## Request 1
**Command:** `curl -i https://jsonplaceholder.typicode.com/users/1`

**Response:**
HTTP/1.1 200 OK
Date: Sun, 16 Aug 2026 05:33:10 GMT
Content-Type: application/json; charset=utf-8
Content-Length: 509
Connection: keep-alive
access-control-allow-credentials: true
Cache-Control: max-age=43200
etag: W/"1fd-+2Y3G3w049iSZtw5t1mzSnunngE"
expires: -1
nel: {"report_to":"heroku-nel","response_headers":["Via"],"max_age":3600,"success_fraction":0.01,"failure_fraction":0.1}
pragma: no-cache
report-to: {"group":"heroku-nel","endpoints":[{"url":"https://nel.heroku.com/reports?s=hcim2HEuPeWVzmNQK6NPKzhenGdnMXEOagm00OjdjcU%3D\u0026sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d\u0026ts=1786848777"}],"max_age":3600}
reporting-endpoints: heroku-nel="https://nel.heroku.com/reports?s=hcim2HEuPeWVzmNQK6NPKzhenGdnMXEOagm00OjdjcU%3D&sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d&ts=1786848777"
Server: cloudflare
vary: Origin, Accept-Encoding
via: 2.0 heroku-router
x-content-type-options: nosniff
x-powered-by: Express
x-ratelimit-limit: 1000
x-ratelimit-remaining: 997
x-ratelimit-reset: 1786848823
Age: 9613
Accept-Ranges: bytes
cf-cache-status: HIT
CF-RAY: a2be100d1ee0fcf3-SIN
alt-svc: h3=":443"; ma=86400

{
  "id": 1,
  "name": "Leanne Graham",
  "username": "Bret",
  "email": "Sincere@april.biz",
  "address": {
    "street": "Kulas Light",
    "suite": "Apt. 556",
    "city": "Gwenborough",
    "zipcode": "92998-3874",
    "geo": {
      "lat": "-37.3159",
      "lng": "81.1496"
    }
  },
  "phone": "1-770-736-8031 x56442",
  "website": "hildegard.org",
  "company": {
    "name": "Romaguera-Crona",
    "catchPhrase": "Multi-layered client-server neural-net",
    "bs": "harness real-time e-markets"
  }
}


## Request 2
**Command:** `curl -i https://jsonplaceholder.typicode.com/posts/1`

**Response:**
HTTP/1.1 200 OK
Date: Sun, 16 Aug 2026 05:35:18 GMT
Content-Type: application/json; charset=utf-8
Content-Length: 292
Connection: keep-alive
access-control-allow-credentials: true
Cache-Control: max-age=43200
etag: W/"124-yiKdLzqO5gfBrJFrcdJ8Yq0LGnU"
expires: -1
nel: {"report_to":"heroku-nel","response_headers":["Via"],"max_age":3600,"success_fraction":0.01,"failure_fraction":0.1}
pragma: no-cache
report-to: {"group":"heroku-nel","endpoints":[{"url":"https://nel.heroku.com/reports?s=PD3aZ5JXmnXLLbuM9yuy2jwg6ke8U5C2Yq%2BT0erzkj0%3D\u0026sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d\u0026ts=1775729378"}],"max_age":3600}
reporting-endpoints: heroku-nel="https://nel.heroku.com/reports?s=PD3aZ5JXmnXLLbuM9yuy2jwg6ke8U5C2Yq%2BT0erzkj0%3D&sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d&ts=1775729378"
Server: cloudflare
vary: Origin, Accept-Encoding
via: 2.0 heroku-router
x-content-type-options: nosniff
x-powered-by: Express
x-ratelimit-limit: 1000
x-ratelimit-remaining: 730
x-ratelimit-reset: 1775729393
Age: 18600
Accept-Ranges: bytes
cf-cache-status: HIT
CF-RAY: a2be132ccb0ffda0-SIN
alt-svc: h3=":443"; ma=86400

{
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}

## Request 3
**Command:** `curl -i https://jsonplaceholder.typicode.com/posts/2`

**Response:**
HTTP/1.1 200 OK
Date: Sun, 16 Aug 2026 05:37:23 GMT
Content-Type: application/json; charset=utf-8
Content-Length: 278
Connection: keep-alive
access-control-allow-credentials: true
Cache-Control: max-age=43200
etag: W/"116-jnDuMpjju89+9j7e0BqkdFsVRjs"
expires: -1
nel: {"report_to":"heroku-nel","response_headers":["Via"],"max_age":3600,"success_fraction":0.01,"failure_fraction":0.1}
pragma: no-cache
report-to: {"group":"heroku-nel","endpoints":[{"url":"https://nel.heroku.com/reports?s=cGXiyNNHOQ22OPxHXWspjwZ4cKHnYz%2Bqv2EeLpZFQMM%3D\u0026sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d\u0026ts=1786839313"}],"max_age":3600}
reporting-endpoints: heroku-nel="https://nel.heroku.com/reports?s=cGXiyNNHOQ22OPxHXWspjwZ4cKHnYz%2Bqv2EeLpZFQMM%3D&sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d&ts=1786839313"
Server: cloudflare
vary: Origin, Accept-Encoding
via: 2.0 heroku-router
x-content-type-options: nosniff
x-powered-by: Express
x-ratelimit-limit: 1000
x-ratelimit-remaining: 999
x-ratelimit-reset: 1786839343
Age: 19329
Accept-Ranges: bytes
cf-cache-status: HIT
CF-RAY: a2be1638af949d17-SIN
alt-svc: h3=":443"; ma=86400

{
  "userId": 1,
  "id": 2,
  "title": "qui est esse",
  "body": "est rerum tempore vitae\nsequi sint nihil reprehenderit dolor beatae ea dolores neque\nfugiat blanditiis voluptate porro vel nihil molestiae ut reiciendis\nqui aperiam non debitis possimus qui neque nisi nulla"
}

## Request 4
**Command:** `curl -i https://jsonplaceholder.typicode.com/comments/1`

**Response:**
HTTP/1.1 200 OK
Date: Sun, 16 Aug 2026 05:38:22 GMT
Content-Type: application/json; charset=utf-8
Content-Length: 268
Connection: keep-alive
access-control-allow-credentials: true
Cache-Control: max-age=43200
etag: W/"10c-KJ4I9RM/+33TKdV8CFsIvqsDSP0"
expires: -1
nel: {"report_to":"heroku-nel","response_headers":["Via"],"max_age":3600,"success_fraction":0.01,"failure_fraction":0.1}
pragma: no-cache
report-to: {"group":"heroku-nel","endpoints":[{"url":"https://nel.heroku.com/reports?s=sL5K4df2Pij6Nfm4O5g41syJQQ9lhbeMKkwGMnShsIo%3D\u0026sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d\u0026ts=1786839170"}],"max_age":3600}
reporting-endpoints: heroku-nel="https://nel.heroku.com/reports?s=sL5K4df2Pij6Nfm4O5g41syJQQ9lhbeMKkwGMnShsIo%3D&sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d&ts=1786839170"
Server: cloudflare
vary: Origin, Accept-Encoding
via: 2.0 heroku-router
x-content-type-options: nosniff
x-powered-by: Express
x-ratelimit-limit: 1000
x-ratelimit-remaining: 999
x-ratelimit-reset: 1786839223
Age: 19531
Accept-Ranges: bytes
cf-cache-status: HIT
CF-RAY: a2be17a98ac97d30-SIN
alt-svc: h3=":443"; ma=86400

{
  "postId": 1,
  "id": 1,
  "name": "id labore ex et quam laborum",
  "email": "Eliseo@gardner.biz",
  "body": "laudantium enim quasi est quidem magnam voluptate ipsam eos\ntempora quo necessitatibus\ndolor quam autem quasi\nreiciendis et nam sapiente accusantium"
}

## Request 5
**Command:** `curl -i https://jsonplaceholder.typicode.com/posts/9999`

**Response:**
HTTP/1.1 404 Not Found
Date: Sun, 16 Aug 2026 05:39:05 GMT
Content-Type: application/json; charset=utf-8
Content-Length: 2
Connection: keep-alive
access-control-allow-credentials: true
Cache-Control: max-age=43200
etag: W/"2-vyGp6PvFo4RvsFtPoIWeCReyIC8"
expires: -1
nel: {"report_to":"heroku-nel","response_headers":["Via"],"max_age":3600,"success_fraction":0.01,"failure_fraction":0.1}
pragma: no-cache
report-to: {"group":"heroku-nel","endpoints":[{"url":"https://nel.heroku.com/reports?s=F1LXAbvf7GLi2L5svI4L%2F%2BBGF%2BF11PEboOO1U5Wzyo0%3D\u0026sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d\u0026ts=1786832359"}],"max_age":3600}
reporting-endpoints: heroku-nel="https://nel.heroku.com/reports?s=F1LXAbvf7GLi2L5svI4L%2F%2BBGF%2BF11PEboOO1U5Wzyo0%3D&sid=e11707d5-02a7-43ef-b45e-2cf4d2036f7d&ts=1786832359"
Server: cloudflare
vary: Origin, Accept-Encoding
via: 2.0 heroku-router
x-content-type-options: nosniff
x-powered-by: Express
x-ratelimit-limit: 1000
x-ratelimit-remaining: 998
x-ratelimit-reset: 1786832383
Age: 26385
cf-cache-status: HIT
CF-RAY: a2be18b44f1e8089-SIN
alt-svc: h3=":443"; ma=86400

{}
**Note:** Status 404 means the resource does not exist on the server; empty JSON body since there's nothing to return.
