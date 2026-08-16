"""Ejecuta un ciclo completo del Orchestrator una sola vez.

Uso:
  cd backend
  ../.venv/bin/python scripts/run_cycle_once.py

Opcional:
  ../.venv/bin/python scripts/run_cycle_once.py --triggered-by manual_cli
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from tortoise import Tortoise

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.orchestrator import OrchestratorAgent
from app.config import TORTOISE_ORM


async def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta un ciclo completo una vez")
    parser.add_argument(
        "--triggered-by",
        default="manual_cli",
        help="Origen registrado en Execution.triggered_by",
    )
    args = parser.parse_args()

    await Tortoise.init(config=TORTOISE_ORM)
    try:
        metadata = await OrchestratorAgent(triggered_by=args.triggered_by).execute()
        print(json.dumps(metadata.model_dump(mode="json"), indent=2, ensure_ascii=False))
        return 0
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
