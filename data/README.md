# Datos de EventRadar

## `seed_sources.json`

Las 5 fuentes decididas en el plan (sección 8.4), con `base_url: null` y
`active: false` hasta que el equipo confirme las URLs exactas. **No se
inventaron URLs** (regla obligatoria del prompt de inicialización). Cargar
con un script propio del equipo una vez confirmadas, o mediante
`POST /api/v1/internal/sources`.

## Pendientes (sección 3.3 del plan)

Los siguientes dos datasets **no se generaron en esta inicialización**
porque no existen en el repositorio ni fueron provistos, y crearlos
implicaría inventar datos:

- `seed_events_san_luis.json`: dataset histórico (~100 eventos de San Luis)
  mencionado en el plan como disponible para el equipo. Falta incorporarlo
  al repositorio si el equipo decide usarlo para probar estructura,
  clasificación y deduplicación (no sirve para validar cobertura ni
  geolocalización de Posadas).
- `evaluation_posadas.json`: dataset etiquetado específico de Posadas (20
  eventos reales o sintéticos controlados, 10 publicaciones que no son
  eventos, 5 duplicados redactados distinto, 5 casos ambiguos). Es un
  bloqueante del checklist del plan (sección 25) y debe construirlo el
  equipo con casos reales o cuidadosamente sintéticos, no un agente
  automatizado.
