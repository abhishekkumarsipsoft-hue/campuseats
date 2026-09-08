"""
C6: one error shape everywhere. Every failure response, from every
endpoint, is built by problem() so the client only ever has to parse
one JSON shape - modelled on RFC 7807 (application/problem+json).
"""
from flask import jsonify

_TYPE_BASE = "https://campuseats.example/problems/"


def problem(status: int, title: str, detail: str):
    body = {
        "type": f"{_TYPE_BASE}{title.lower().replace(' ', '-')}",
        "title": title,
        "status": status,
        "detail": detail,
    }
    resp = jsonify(body)
    resp.status_code = status
    resp.headers["Content-Type"] = "application/problem+json"
    return resp
