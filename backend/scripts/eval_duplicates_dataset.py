"""Evalua el dataset de duplicados con el Evaluator real.

Uso:
  cd backend
  python3 scripts/eval_duplicates_dataset.py

Opcional:
  python3 scripts/eval_duplicates_dataset.py --dataset ../data/evaluation_duplicates.json
  python3 scripts/eval_duplicates_dataset.py --no-strict
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.evaluator import EvaluatorAgent
from app.domain.entities import EventCandidate
from app.domain.enums import EvaluationDecisionType, ProcessingStatus


def _default_dataset_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_duplicates.json"


def _candidate_payload(payload: dict) -> dict:
    data = dict(payload)
    data.setdefault("is_event", True)
    data.setdefault("confidence", 0.9)
    data.setdefault("processing_status", ProcessingStatus.GEOLOCATED)
    data.setdefault("source_id", str(uuid4()))
    return data


def _load_cases(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("El dataset debe ser una lista de casos")
    return [dict(item) for item in payload if isinstance(item, dict)]


async def _run_case(case: dict) -> dict:
    candidate = EventCandidate.model_validate(_candidate_payload(case["candidate"]))
    existing = EventCandidate.model_validate(_candidate_payload(case["existing"]))
    evaluator = EvaluatorAgent(existing_events=[existing])
    result = await evaluator.execute(candidate)

    expected = case.get("expected", {})
    expected_decision = expected.get("decision")
    expected_score_min = expected.get("score_min")

    ok = True
    if expected_decision is not None:
        ok = ok and result.decision == EvaluationDecisionType(expected_decision)
    if expected_score_min is not None:
        ok = ok and (result.score is not None and result.score >= float(expected_score_min))

    return {
        "id": case.get("id"),
        "ok": ok,
        "decision": result.decision,
        "score": result.score,
        "duplicate_of": str(result.duplicate_of) if result.duplicate_of is not None else None,
        "reasons": result.reasons,
        "expected": expected,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Evalua duplicados con RapidFuzz")
    parser.add_argument("--dataset", type=Path, default=_default_dataset_path())
    parser.add_argument("--no-strict", action="store_true", help="No falla con mismatches")
    args = parser.parse_args()

    cases = _load_cases(args.dataset)
    results = [await _run_case(case) for case in cases]

    counts = Counter("ok" if item["ok"] else "fail" for item in results)
    decisions = Counter(str(item["decision"]) for item in results)

    print(f"Dataset: {args.dataset}")
    print(f"Casos: {len(results)}")
    print(f"OK: {counts['ok']} / FAIL: {counts['fail']}")
    print("Decisiones:")
    for decision, amount in sorted(decisions.items()):
        print(f"  {decision}: {amount}")

    failed = [item for item in results if not item["ok"]]
    if failed:
        print("\nMismatches:")
        for item in failed:
            print(
                f"- {item['id']}: decision={item['decision']} score={item['score']} expected={item['expected']}"
            )

    return 1 if failed and not args.no_strict else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
