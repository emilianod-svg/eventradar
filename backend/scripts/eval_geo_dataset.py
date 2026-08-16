"""Evalua el dataset geográfico de Posadas.

Uso:
  cd backend
  ../.venv/bin/python scripts/eval_geo_dataset.py

Opcional:
  ../.venv/bin/python scripts/eval_geo_dataset.py --dataset ../data/evaluation_posadas.json
  ../.venv/bin/python scripts/eval_geo_dataset.py --format json
  ../.venv/bin/python scripts/eval_geo_dataset.py --no-strict
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.evaluator import EvaluatorAgent
from app.agents.geo_classifier import GeoClassifierAgent
from app.domain.errors import ExternalServiceNotConfiguredError


class EmptyGeocodingClient:
    async def geocode(self, *, query: str) -> dict:
        return {}


def _default_dataset_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_posadas.json"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Evalua el dataset geográfico de Posadas")
    parser.add_argument("--dataset", type=Path, default=_default_dataset_path())
    parser.add_argument(
        "--format",
        choices={"markdown", "json"},
        default="markdown",
        help="Formato de salida del reporte",
    )
    parser.add_argument("--no-strict", action="store_true", help="No falla con mínimos")
    args = parser.parse_args()

    agent = EvaluatorAgent(existing_events=[])
    try:
        report = await agent.evaluate_dataset(args.dataset)
    except ExternalServiceNotConfiguredError:
        offline_classifier = GeoClassifierAgent(geocoding_client=EmptyGeocodingClient())
        report = await agent.evaluate_dataset(args.dataset, classifier=offline_classifier.classify)
        print("[warn] Geocoding no configurado; evaluando en modo offline con catálogo local.\n")

    if args.format == "json":
        print(report.to_json())
    else:
        print(report.to_markdown())

    if args.no_strict:
        return 0

    if report.accuracy < 0.80:
        return 1
    if report.precision < 0.75:
        return 1
    if report.recall < 0.75:
        return 1
    if report.f1 < 0.75:
        return 1
    if report.geocoding_coverage < 0.80:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
