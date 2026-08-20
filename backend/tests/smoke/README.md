# Smoke tests reales (sección 18.2 del plan)

Nivel "Smoke real: fuentes reales, fuera del CI obligatorio" de la pirámide
de pruebas. A diferencia de las pruebas unitarias/de agentes (que mockean el
LLM), estos tests llaman a un LLM real y verifican que la integración
funciona de punta a punta — no miden precisión formal.

Se marcan con `@pytest.mark.llm_smoke` y se saltan automáticamente salvo que
se corran explícitamente:

```bash
export RUN_LLM_SMOKE_TESTS=1
# Requiere Ollama corriendo y el modelo de LLM_MODEL disponible:
#   ollama pull minimax-m3:cloud   (o el valor configurado en .env)
pytest tests/smoke -m llm_smoke -v
```

La medición formal de precisión (≥0.80, sección 18.1/18.3) se hace contra
el dataset etiquetado de Posadas (20/10/5/5), documentado como tarea
separada — no vive en este directorio.
