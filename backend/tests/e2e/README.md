# Tests E2E determinísticos

`test_full_cycle_deterministic.py` cubre el ciclo completo con fuentes
simuladas (sección 18.2): 3 fuentes (Scrapy + 2 RSS) con fixtures HTML/XML
versionadas fluyen por `OrchestratorAgent` real —
Collector → Analyzer → GeoClassifier → Evaluator → Persistence — con solo
el LLM y el geocoding fakeados. Verifica deduplicación cruzada entre
fuentes en el mismo ciclo, `event_sources` con las 3 fuentes vinculadas,
aprendizaje y una segunda corrida idempotente.

Requiere Postgres real (`@pytest.mark.integration`, se salta si no hay
`TEST_DATABASE_URL`/`DATABASE_URL` configuradas — ver `tests/conftest.py`).
