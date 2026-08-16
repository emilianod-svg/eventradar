# Datos de EventRadar

## `seed_sources.json`

Las 5 fuentes decididas en el plan (sección 8.4), con `base_url: null` y
`active: false` hasta que el equipo confirme las URLs exactas. **No se
inventaron URLs** (regla obligatoria del prompt de inicialización). Cargar
con un script propio del equipo una vez confirmadas, o mediante
`POST /api/v1/internal/sources`.

## `evaluation_posadas.json`

Dataset etiquetado específico de Posadas para evaluar geocodificación,
normalización, umbrales y resiliencia. Incluye casos válidos, ambiguos,
inválidos y con errores ortográficos, además de abreviaturas y ubicaciones
fuera de alcance.

## `seed_events_san_luis.json`

El dataset histórico mencionado en el plan sigue pendiente de incorporación.
No se generó automáticamente porque no fue provisto en el repositorio.
