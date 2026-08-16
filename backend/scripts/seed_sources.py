"""Carga `data/seed_sources.json` en la tabla `sources`.

Uso:
  cd backend
  ../.venv/bin/python scripts/seed_sources.py

Opcional:
  ../.venv/bin/python scripts/seed_sources.py --dry-run
  ../.venv/bin/python scripts/seed_sources.py --dataset ../data/seed_sources.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from tortoise import Tortoise

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import TORTOISE_ORM
from app.models.source import Source


def _default_dataset_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "seed_sources.json"


def _load_sources(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("El dataset debe ser una lista de fuentes")
    return [dict(item) for item in payload if isinstance(item, dict)]


def _normalize_payload(item: dict) -> dict:
    payload = dict(item)
    payload["name"] = str(payload["name"]).strip()
    payload["base_url"] = payload.get("base_url")
    if isinstance(payload["base_url"], str):
        payload["base_url"] = payload["base_url"].strip()
    payload["adapter_type"] = str(payload["adapter_type"]).strip()
    payload["active"] = bool(payload.get("active", True))
    payload["reliability_score"] = float(payload.get("reliability_score", 0.5))
    notes = payload.get("notes")
    if notes is not None:
        payload["contact_notes"] = str(notes).strip()
    return payload


async def _upsert_source(payload: dict, *, dry_run: bool) -> tuple[str, Source | None]:
    normalized = _normalize_payload(payload)
    if not normalized.get("base_url"):
        return "skipped_no_base_url", None

    if dry_run:
        return "would_create", None

    existing = await Source.get_or_none(base_url=normalized["base_url"])
    if existing is None:
        existing = await Source.get_or_none(name=normalized["name"])

    if existing is None:
        source = await Source.create(**normalized)
        return "create", source

    for field in ("name", "base_url", "adapter_type", "active", "reliability_score"):
        setattr(existing, field, normalized[field])
    if "contact_notes" in normalized:
        existing.contact_notes = normalized["contact_notes"]
    await existing.save()
    return "update", existing


async def main() -> int:
    parser = argparse.ArgumentParser(description="Carga fuentes iniciales")
    parser.add_argument("--dataset", type=Path, default=_default_dataset_path())
    parser.add_argument("--dry-run", action="store_true", help="No escribe en la base")
    args = parser.parse_args()

    sources = _load_sources(args.dataset)
    try:
        if not args.dry_run:
            await Tortoise.init(config=TORTOISE_ORM)

        created = 0
        updated = 0
        skipped = 0

        for payload in sources:
            action, source = await _upsert_source(payload, dry_run=args.dry_run)
            if action in {"create", "would_create"}:
                created += 1
            elif action == "update":
                updated += 1
            else:
                skipped += 1

            print(f"{action.upper():6} {payload['name']} | {payload['base_url']}")

        print(
            f"\nResumen: create={created} update={updated} "
            f"skipped={skipped} dry_run={args.dry_run}"
        )
        return 0
    finally:
        if not args.dry_run:
            await Tortoise.close_connections()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
