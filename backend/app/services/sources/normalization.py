"""Normalización de URLs y adaptadores de fuentes."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}


def normalize_adapter_type(value: str) -> str:
    normalized = value.strip().casefold()
    if normalized in {"rss_feed", "rss-feed", "feed", "atom"}:
        return "rss"
    if normalized in {"scrapy_static", "scrapy-static", "static", "html"}:
        return "scrapy"
    return normalized


def normalize_source_url(value: str) -> str | None:
    if not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate:
        return None

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    hostname = parsed.hostname
    if not hostname:
        return None

    try:
        port = parsed.port
    except ValueError:
        return None

    netloc = hostname.casefold()
    if port is not None:
        default_port = (parsed.scheme == "http" and port == 80) or (
            parsed.scheme == "https" and port == 443
        )
        if not default_port:
            netloc = f"{netloc}:{port}"

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in _TRACKING_QUERY_KEYS
    ]
    filtered_query.sort(key=lambda item: (item[0].casefold(), item[1]))
    query = urlencode(filtered_query, doseq=True)

    return urlunparse((parsed.scheme.casefold(), netloc, path, "", query, ""))
