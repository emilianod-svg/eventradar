"""BayesianReliabilityScorer: suavizado bayesiano (sección 14.1)."""

from __future__ import annotations

import pytest
from app.services.scoring.base import BayesianReliabilityScorer, get_reliability_scorer


def test_get_reliability_scorer_returns_bayesian_implementation() -> None:
    assert isinstance(get_reliability_scorer(), BayesianReliabilityScorer)


def test_compute_matches_formula_from_section_14_1() -> None:
    scorer = BayesianReliabilityScorer()

    result = scorer.compute(previous_score=0.5, accepted=8, processed=10, extraction_quality=0.8)

    acceptance_score = (8 + 2) / (10 + 4)
    expected = 0.5 * 0.40 + acceptance_score * 0.40 + 0.8 * 0.20
    assert result == pytest.approx(expected)


def test_compute_with_zero_processed_uses_prior_without_crashing() -> None:
    scorer = BayesianReliabilityScorer()

    result = scorer.compute(previous_score=0.5, accepted=0, processed=0, extraction_quality=0.0)

    # acceptance_score = (0+2)/(0+4) = 0.5 — ni castiga ni premia a una
    # fuente sin observaciones todavía.
    assert result == pytest.approx(0.5 * 0.40 + 0.5 * 0.40 + 0.0 * 0.20)


def test_compute_never_exceeds_one_even_with_near_perfect_inputs() -> None:
    scorer = BayesianReliabilityScorer()

    result = scorer.compute(previous_score=1.0, accepted=100, processed=100, extraction_quality=1.0)

    # El suavizado bayesiano nunca llega a acceptance_score=1.0 exacto
    # (siempre hay +2/+4 de prior), así que el score compuesto tampoco
    # satura en 1.0 aunque todo sea "perfecto" — es el comportamiento
    # esperado, no un bug.
    assert 0.0 <= result <= 1.0
    assert result == pytest.approx(0.9923076923076923)


def test_compute_stays_bounded_when_everything_rejected() -> None:
    scorer = BayesianReliabilityScorer()

    result = scorer.compute(previous_score=0.0, accepted=0, processed=50, extraction_quality=0.0)

    assert result >= 0.0
