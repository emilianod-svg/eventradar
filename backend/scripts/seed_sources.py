"""Carga `data/source_catalog.json` en la tabla `sources`.

Uso:
  cd backend
  ../.venv/bin/python scripts/seed_sources.py

Opcional:
  ../.venv/bin/python scripts/seed_sources.py --dry-run
  ../.venv/bin/python scripts/seed_sources.py --dataset ../data/source_catalog.json
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from tortoise import Tortoise

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import TORTOISE_ORM
from app.services.sources.bootstrap import SourceBootstrapService
from app.services.sources.catalog import load_source_catalog


def _default_dataset_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "source_catalog.json"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Carga fuentes iniciales")
    parser.add_argument("--dataset", type=Path, default=_default_dataset_path())
    parser.add_argument("--dry-run", action="store_true", help="No escribe en la base")
    args = parser.parse_args()

    catalog = load_source_catalog(args.dataset)
    if args.dry_run:
        print(f"DRY_RUN configured={len(catalog.entries)} dataset={args.dataset}")
        return 0

    await Tortoise.init(config=TORTOISE_ORM)
    try:
        report = await SourceBootstrapService(catalog_path=str(args.dataset)).bootstrap(catalog)
        print(
            "BOOTSTRAP "
            f"configured={report.configured} inserted={report.inserted} "
            f"updated={report.updated} unchanged={report.unchanged} invalid={report.invalid}"
        )
        return 0
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
