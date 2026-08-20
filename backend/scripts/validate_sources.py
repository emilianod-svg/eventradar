"""Valida el catálogo declarado en `data/source_catalog.json`.

Uso:
  cd backend
  ../.venv/bin/python scripts/validate_sources.py

Opcional:
  ../.venv/bin/python scripts/validate_sources.py --discover
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.sources.catalog import load_source_catalog
from app.services.sources.validation import SourceValidationService


def _default_dataset_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "source_catalog.json"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Valida fuentes iniciales")
    parser.add_argument("--dataset", type=Path, default=_default_dataset_path())
    parser.add_argument("--discover", action="store_true", help="Muestra candidatos de feeds")
    args = parser.parse_args()

    catalog = load_source_catalog(args.dataset)
    validator = SourceValidationService()

    for entry in catalog.entries:
        result = await validator.validate_catalog_entry(entry)
        discovered_text = ""
        if args.discover and result.discovered_urls:
            discovered_text = " discovered=" + ",".join(result.discovered_urls)
        print(
            f"{result.status.upper():7} {entry.name} | {entry.base_url} | "
            f"final={result.final_url or '-'} | error={result.error or '-'}{discovered_text}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
