"""Pruebas del dataset etiquetado de Posadas."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def test_evaluation_posadas_dataset_contains_required_case_types() -> None:
    dataset_path = Path(__file__).resolve().parents[3] / "data" / "evaluation_posadas.json"
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))

    counts = Counter(item["case_type"] for item in payload)

    assert counts["valid"] >= 20
    assert counts["ambiguous"] >= 10
    assert counts["invalid"] >= 5
    assert counts["typo"] >= 5
    assert len(payload) >= 40
