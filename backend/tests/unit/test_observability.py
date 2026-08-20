"""Pruebas del formatter de logging estructurado."""

from __future__ import annotations

import logging

from app.observability import CorrelationIdFilter, ExtraFieldsFormatter


def _make_record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.services.llm.ollama",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="llm_extract_invalid_json",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formatter_prints_extra_fields() -> None:
    formatter = ExtraFieldsFormatter(
        fmt=(
            "%(asctime)s level=%(levelname)s logger=%(name)s "
            "correlation_id=%(correlation_id)s message=%(message)s"
        )
    )
    record = _make_record(correlation_id="-", model="minimax-m3", attempt=2, latency_ms=123.4)

    output = formatter.format(record)

    assert "message=llm_extract_invalid_json" in output
    assert "model=minimax-m3" in output
    assert "attempt=2" in output
    assert "latency_ms=123.4" in output


def test_formatter_escapes_newlines_in_extra_values() -> None:
    formatter = ExtraFieldsFormatter(fmt="%(message)s")
    record = _make_record(correlation_id="-", raw_output_preview="line one\nline two")

    output = formatter.format(record)

    assert "\n" not in output
    assert "raw_output_preview=line one\\nline two" in output


def test_formatter_without_extra_fields_matches_base_output() -> None:
    formatter = ExtraFieldsFormatter(fmt="%(message)s")
    record = _make_record(correlation_id="-")

    assert formatter.format(record) == "llm_extract_invalid_json"


def test_correlation_id_filter_sets_default_when_unset() -> None:
    filter_ = CorrelationIdFilter()
    record = _make_record()

    assert filter_.filter(record) is True
    assert record.correlation_id == "-"
