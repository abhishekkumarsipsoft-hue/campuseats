"""
A6 C3: content negotiation. The service can produce application/json
(default) and application/xml. Anything else -> 406.
"""
import xml.etree.ElementTree as ET

# What each format answers to in an Accept header.
_FORMATS = {
    "json": ("application/json", "application/problem+json"),
    "xml": ("application/xml", "text/xml", "application/problem+xml"),
}

_SINGULAR = {"orders": "order", "items": "item", "errors": "error"}


def _parse_accept(header):
    ranges = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        segs = [s.strip() for s in part.split(";")]
        q = 1.0
        for s in segs[1:]:
            if s.lower().startswith("q="):
                try:
                    q = float(s[2:])
                except ValueError:
                    q = 0.0
        ranges.append((segs[0].lower(), q))
    return ranges


def _quality(fmt, ranges):
    """q-value of the most specific media range that matches this format."""
    best_spec, best_q = -1, 0.0
    for media, q in ranges:
        if media in _FORMATS[fmt]:
            spec = 2
        elif media == "application/*":
            spec = 1
        elif media == "*/*":
            spec = 0
        else:
            continue
        if spec > best_spec:
            best_spec, best_q = spec, q
    return best_q


def negotiate(accept_header):
    """Return 'json', 'xml', or None (-> 406). Missing Accept means JSON."""
    if accept_header is None or not accept_header.strip():
        return "json"
    ranges = _parse_accept(accept_header)
    best_fmt, best_q = None, 0.0
    for fmt in ("json", "xml"):          # json first: wins ties (e.g. */*)
        q = _quality(fmt, ranges)
        if q > best_q:
            best_fmt, best_q = fmt, q
    return best_fmt


def _build(tag, value):
    el = ET.Element(tag)
    if isinstance(value, dict):
        for k, v in value.items():
            el.append(_build(k, v))
    elif isinstance(value, list):
        child = _SINGULAR.get(tag, "item")
        for v in value:
            el.append(_build(child, v))
    elif value is None:
        el.set("nil", "true")
    elif isinstance(value, bool):
        el.text = "true" if value else "false"
    else:
        el.text = str(value)
    return el


def to_xml(root_tag, data):
    body = ET.tostring(_build(root_tag, data), encoding="utf-8")
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + body
