"""Repara duplicados en `sources` causados por `canonical_base_url` sin normalizar.

Contexto: la migración `2_20260817000000_source_catalog_bootstrap.py` backfilleó
`canonical_base_url = base_url` tal cual, sin pasar por `normalize_source_url()`
(que recorta barras finales, entre otras cosas). Como `SourceBootstrapService`
busca filas existentes por el canonical *normalizado* en cada arranque del
backend, cualquier fila cuyo `base_url` original tuviera una barra final quedó
con un `canonical_base_url` que ya no matcheaba nada -> el bootstrap la trató
como "nueva" e insertó un duplicado activo. Eso duplicó la carga sobre Ollama
en la ejecución del 2026-08-17 13:08 (429 Too Many Requests, ~38% de ítems
fallidos).

Este script:
  1. Recalcula el canonical_base_url correcto (vía `normalize_source_url`)
     para cada fila.
  2. Agrupa las fuentes activas por ese canonical correcto.
  3. Si un grupo tiene más de una fila activa, conserva la más antigua
     (`created_at` mínimo) como sobreviviente -con su canonical corregido- y
     desactiva el resto (`active=False`, `canonical_base_url=None`,
     `validation_status='duplicate_inactive'`), igual que hace la migración
     original con sus propios duplicados.
  4. Si un grupo tiene una sola fila activa pero con canonical desalineado,
     sólo lo corrige (sin desactivar nada).

Uso:
  cd backend
  ../.venv/bin/python scripts/repair_duplicate_sources.py
  ../.venv/bin/python scripts/repair_duplicate_sources.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from tortoise import Tortoise
from tortoise.transactions import in_transaction

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import TORTOISE_ORM
from app.models.source import Source
from app.services.sources.normalization import normalize_source_url

_BOOTSTRAP_LOCK_KEY = 314159265


@dataclass(slots=True)
class RepairReport:
    groups_with_duplicates: int = 0
    sources_deactivated: int = 0
    canonical_corrected: int = 0
    skipped_no_active_survivor: list[str] = field(default_factory=list)


async def repair(dry_run: bool) -> RepairReport:
    report = RepairReport()
    sources = await Source.all()

    by_canonical: dict[str, list[Source]] = defaultdict(list)
    for source in sources:
        normalized = normalize_source_url(source.base_url)
        if normalized is None:
            continue
        by_canonical[normalized].append(source)

    async with in_transaction() as conn:
        if not dry_run:
            await conn.execute_query(f"SELECT pg_advisory_xact_lock({_BOOTSTRAP_LOCK_KEY})")

        for normalized, group in by_canonical.items():
            active_rows = [s for s in group if s.active]

            if len(active_rows) > 1:
                report.groups_with_duplicates += 1
                survivor = min(active_rows, key=lambda s: s.created_at)
                losers = [s for s in active_rows if s.id != survivor.id]

                print(
                    f"DUPLICATE canonical={normalized!r} "
                    f"survivor={survivor.id} ({survivor.name}, created_at={survivor.created_at}) "
                    f"deactivating={[str(s.id) for s in losers]}"
                )

                if survivor.canonical_base_url != normalized:
                    report.canonical_corrected += 1
                    if not dry_run:
                        survivor.canonical_base_url = normalized
                        await survivor.save(update_fields=["canonical_base_url"])

                for loser in losers:
                    report.sources_deactivated += 1
                    if not dry_run:
                        loser.active = False
                        loser.canonical_base_url = None
                        loser.validation_status = "duplicate_inactive"
                        await loser.save(
                            update_fields=["active", "canonical_base_url", "validation_status"]
                        )
                continue

            if len(active_rows) == 1:
                survivor = active_rows[0]
                if survivor.canonical_base_url != normalized:
                    report.canonical_corrected += 1
                    print(
                        f"REALIGN canonical={normalized!r} source={survivor.id} ({survivor.name}) "
                        f"old_canonical={survivor.canonical_base_url!r}"
                    )
                    if not dry_run:
                        survivor.canonical_base_url = normalized
                        await survivor.save(update_fields=["canonical_base_url"])
                continue

            if len(group) > 1:
                report.skipped_no_active_survivor.append(normalized)

    return report


async def main() -> int:
    parser = argparse.ArgumentParser(description="Repara duplicados de sources")
    parser.add_argument("--dry-run", action="store_true", help="No escribe en la base")
    args = parser.parse_args()

    await Tortoise.init(config=TORTOISE_ORM)
    try:
        report = await repair(dry_run=args.dry_run)
        print(
            "REPAIR "
            f"dry_run={args.dry_run} groups_with_duplicates={report.groups_with_duplicates} "
            f"sources_deactivated={report.sources_deactivated} "
            f"canonical_corrected={report.canonical_corrected}"
        )
        if report.skipped_no_active_survivor:
            print(
                "SKIPPED (sin fila activa, requiere revisión manual): "
                f"{report.skipped_no_active_survivor}"
            )
        return 0
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
