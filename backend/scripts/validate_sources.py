"""Valida fuentes declaradas en `data/seed_sources.json`.

Uso:
  cd backend
  ../.venv/bin/python scripts/validate_sources.py

Opcional:
  ../.venv/bin/python scripts/validate_sources.py --check-access
  ../.venv/bin/python scripts/validate_sources.py --allowed-hosts ticketmisiones.com,misionesonline.net
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings


def _default_dataset_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "seed_sources.json"


@dataclass(slots=True)
class SourceCheck:
    name: str
    base_url: str | None
    active: bool
    ok: bool
    skipped: bool
    reasons: list[str]


def _load_sources(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("El dataset debe ser una lista de fuentes")
    return [dict(item) for item in payload if isinstance(item, dict)]


def _allowed_hosts_from_args(raw: str | None) -> set[str]:
    if raw is None:
        raw = get_settings().evaluation_allowed_source_hosts
    return {host.strip().casefold() for host in raw.split(",") if host.strip()}


def _check_url(base_url: object, *, allowed_hosts: set[str]) -> tuple[str | None, list[str]]:
    reasons: list[str] = []
    if not isinstance(base_url, str) or not base_url.strip():
        return None, ["missing_base_url"]

    url = base_url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        reasons.append("invalid_scheme")
    if not parsed.netloc:
        reasons.append("missing_host")

    host = (parsed.hostname or "").casefold()
    if allowed_hosts and host and not any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts):
        reasons.append("host_not_allowed")

    return url, reasons


async def _check_access(url: str) -> tuple[bool, str | None]:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.head(url)
            if response.status_code in {405, 501}:
                response = await client.get(url)
            return response.status_code < 400, f"http_{response.status_code}"
    except Exception as exc:
        return False, exc.__class__.__name__


async def main() -> int:
    parser = argparse.ArgumentParser(description="Valida fuentes seed")
    parser.add_argument("--dataset", type=Path, default=_default_dataset_path())
    parser.add_argument("--allowed-hosts", default=None)
    parser.add_argument("--check-access", action="store_true", help="Hace request real a cada URL")
    args = parser.parse_args()

    allowed_hosts = _allowed_hosts_from_args(args.allowed_hosts)
    sources = _load_sources(args.dataset)

    checks: list[SourceCheck] = []
    for item in sources:
        name = str(item.get("name") or "<sin nombre>")
        active = bool(item.get("active", False))
        url, reasons = _check_url(item.get("base_url"), allowed_hosts=allowed_hosts)
        skipped = False
        ok = not reasons

        if url is None and not active:
            skipped = True
            ok = True
            reasons = ["placeholder_inactive"]

        if args.check_access and url is not None:
            accessible, access_reason = await _check_access(url)
            if not accessible:
                reasons.append(f"not_accessible:{access_reason}")
                ok = False

        checks.append(
            SourceCheck(name=name, base_url=url, active=active, ok=ok, skipped=skipped, reasons=reasons)
        )

    for check in checks:
        status = "SKIP" if check.skipped else ("OK" if check.ok else "FAIL")
        active = "active" if check.active else "inactive"
        base_url = check.base_url or "<none>"
        reason_text = ", ".join(check.reasons) if check.reasons else "-"
        print(f"{status:4} {check.name} | {active} | {base_url} | {reason_text}")

    failures = sum(1 for check in checks if not check.ok)
    print(f"\nResumen: total={len(checks)} ok={len(checks) - failures} fail={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
