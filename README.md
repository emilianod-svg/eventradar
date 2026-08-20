# EventRadar

Sistema multiagente que convierte publicaciones dispersas de portales locales en
eventos estructurados, deduplicados y geolocalizados para **Posadas, Misiones**.

| Recurso | URL |
|---|---|
| Aplicación web | http://eventradar.dedyn.io |
| API | http://api.eventradar.dedyn.io |
| Estado del servicio | http://api.eventradar.dedyn.io/health |
| Documentación de la API | http://api.eventradar.dedyn.io/docs |

> Usar `http://`, no `https://`. El certificado TLS todavía no fue emitido para
> estos dominios; forzar HTTPS produce un error de handshake
> (`tlsv1 unrecognized name`). Es la corrección pendiente de mayor prioridad.

## Qué hace

La información sobre qué pasa en Posadas está dispersa en notas de portales de
noticias, feeds RSS y páginas de la municipalidad, con fechas escritas en
lenguaje natural («el próximo sábado», «del 3 al 13 de septiembre»), lugares
nombrados de forma ambigua («Auditorium Montoya») y sin coordenadas.

EventRadar recolecta esas publicaciones, extrae los eventos con un modelo de
lenguaje, resuelve la ubicación consultando varios geocodificadores, decide con
reglas auditables si el evento se acepta, se fusiona con uno existente, se manda
a revisión o se descarta, y aprende qué fuentes le sirven. Todo lo publicado
conserva la trazabilidad completa hasta el texto que lo originó.

Estado actual en producción: **13 eventos activos** extraídos de publicaciones
reales, dentro de un radio de 15 km del centro de Posadas.

## Arquitectura

Monolito modular: los agentes son módulos de un mismo proceso FastAPI
(`backend/app/agents/`), no microservicios. Las integraciones externas están
detrás de interfaces en `backend/app/services/` y `backend/app/sources/`.

```
Fuentes RSS/HTML
      │
      ▼
[Recolector]      hash SHA-256, descarta lo ya visto        → raw_contents
      │
      ▼
[Analizador]      IA · LLM vía Ollama, prompt analyzer-v3   → classifications
      │
      ▼
[Clasificador     IA · catálogo local → Nominatim →
 Geográfico]      LocationIQ → Geoapify, consenso 2/300 m
      │
      ▼
[Evaluador]       RapidFuzz + reglas duras, sin LLM
      │           → ACCEPT / MERGE / REVIEW / REJECT        → evaluation_decisions
      ▼
[Persistencia]    transacción única + scoring bayesiano     → events, source_score_history
      │
      └──► el reliability_score aprendido condiciona el ciclo siguiente

Todo el ciclo lo secuencia el [Orquestador], que aísla fallos por fuente y por item.
```

| Agente | Naturaleza | Qué decide |
|---|---|---|
| Orquestador | Determinista | Si puede iniciarse un ciclo (lock), qué fuentes procesar y cómo aislar cada fallo |
| Recolector | Determinista | Qué contenido es nuevo, antes de gastar una llamada al LLM |
| Analizador | **IA (LLM)** | Si un texto describe eventos, cuántos y con qué confianza |
| Clasificador Geográfico | **IA + reglas** | Dónde ocurre el evento, con consenso entre proveedores |
| Evaluador | Determinista | Aceptar, fusionar, mandar a revisión o rechazar |
| Persistencia y Aprendizaje | Determinista | Qué se escribe y cómo cambia la confiabilidad de cada fuente |
| Descubridor de Fuentes | *No implementado* | Quedó fuera de alcance; el Orquestador funciona sin él |

Solo dos de los seis agentes implementados usan modelos. Toda la lógica de
decisión es determinista y deja registro explicable de cada elección.

Diagramas completos (arquitectura, flujo de agentes, UML de secuencia, clases y
casos de uso) en `report/entrega/diagramas/`, con su código Mermaid.

## Stack

| Componente | Tecnología |
|---|---|
| Frontend | React 18 + TypeScript 5.6 + Vite 5.4 |
| Backend | Python 3.11 + FastAPI 0.115 |
| ORM y migraciones | Tortoise ORM 0.21 + Aerich |
| Base de datos | PostgreSQL 16 |
| Modelo de IA | Cliente Ollama · modelo `minimax-m3` (alojado, no local) |
| Geocodificación | Catálogo propio + Nominatim + LocationIQ + Geoapify |
| Deduplicación | RapidFuzz 3.9 + reglas de fecha y ubicación |
| Planificación | APScheduler 3.10 in-process + watchdog |
| Despliegue | Docker Compose · Oracle Cloud · nginx-proxy |
| CI | GitHub Actions (lint, tipos, tests, build, auditoría, gitleaks) |

## Requisitos

- Python 3.11 o 3.12
- Node.js 20+
- Docker y Docker Compose v2
- PostgreSQL 16 (si se corre el backend sin Docker)

## Inicio rápido con Docker Compose

```bash
cp .env.example .env
# completar al menos POSTGRES_PASSWORD y ADMIN_API_KEY con valores propios
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- PostgreSQL: localhost:5433 (expuesto solo para debug local)

## Inicio local sin Docker

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
aerich upgrade                 # aplica las migraciones
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend lee `VITE_API_URL` desde el `.env` de la **raíz** del repositorio
(`vite.config.ts` define `envDir: ".."`), no desde `frontend/.env`.

## Correr un ciclo completo

Por API (requiere la credencial administrativa):

```bash
curl -X POST http://localhost:8000/api/v1/internal/cycles -H "X-Admin-Api-Key: $ADMIN_API_KEY"
```

Por línea de comandos:

```bash
cd backend && ../.venv/bin/python scripts/run_cycle_once.py
```

También puede dispararse desde la pestaña **Ciclos** del frontend, cargando la
credencial administrativa. El scheduler automático está deshabilitado por
defecto (`SCHEDULER_ENABLED=false`); cuando se activa corre según
`SCHEDULER_CRON` (por defecto, lunes y viernes a las 09:00).

Otros comandos disponibles:

```bash
cd backend
../.venv/bin/python scripts/seed_sources.py         # carga el catálogo de fuentes
../.venv/bin/python scripts/validate_sources.py     # verifica que las fuentes respondan
../.venv/bin/python scripts/eval_geo_dataset.py     # evalúa la geolocalización contra el dataset
../.venv/bin/python scripts/eval_duplicates_dataset.py
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del proceso (no consulta la base) |
| GET | `/ready` | Verifica la conexión a PostgreSQL |
| GET | `/api/v1/events` | Listado paginado con filtros `query`, `category`, `date_from`, `date_to` |
| GET | `/api/v1/events/{id-o-slug}` | Detalle de un evento con su fuente |
| GET | `/api/v1/categories` | Categorías activas — **defecto conocido: devuelve 500** |
| GET/POST/PATCH | `/api/v1/internal/sources` | Administración de fuentes |
| POST/GET | `/api/v1/internal/cycles` | Dispara un ciclo · lista ejecuciones y métricas |
| GET | `/api/v1/internal/reviews` | Cola de revisión manual |
| GET | `/docs`, `/openapi.json` | Documentación autogenerada |

Las rutas `/api/v1/internal/*` requieren el encabezado `X-Admin-Api-Key`.

## Tests y calidad

```bash
cd backend
ruff check . && ruff format --check .
mypy app
TEST_DATABASE_URL=postgres://... pytest      # 153 tests, 83 % de cobertura
```

```bash
cd frontend
npm run lint && npm run typecheck && npm test && npm run build
```

Sin `TEST_DATABASE_URL` los tests de integración se omiten. Los tests de humo
contra el LLM real requieren además `RUN_LLM_SMOKE_TESTS=1`.

La integración continua (`.github/workflows/ci.yml`) corre en cada pull request:
lint, tipos y tests del backend contra un PostgreSQL real, lint/tipos/tests/build
del frontend, build de ambas imágenes Docker, `pip-audit`, `npm audit` y
escaneo de secretos con `gitleaks`.

## Configuración

Ver `.env.example` para el listado completo y comentado. Los umbrales de
decisión son variables de entorno, de modo que ajustar la severidad del sistema
no requiere volver a desplegar:

| Variable | Valor por defecto | Efecto |
|---|---|---|
| `CONFIDENCE_REVIEW_THRESHOLD` | 0.50 | Por debajo, el candidato se rechaza |
| `CONFIDENCE_ACCEPT_THRESHOLD` | 0.70 | Entre ambos, se acepta marcado para revisión |
| `DUPLICATE_REVIEW_THRESHOLD` | 0.75 | A partir de aquí va a revisión humana |
| `DUPLICATE_AUTO_MERGE_THRESHOLD` | 0.90 | Fusión automática, si además coinciden fecha y lugar |
| `GEO_CONFIDENCE_REVIEW_THRESHOLD` | 0.75 | Por debajo, queda en `pending_review` |
| `SEARCH_RADIUS_KM` | 15 | Distancia máxima al centro de Posadas |
| `SCHEDULER_ENABLED` | false | Activa el ciclo automático |

La configuración se valida al arrancar: umbrales incoherentes entre sí, CORS en
`*` o `ADMIN_API_KEY` ausente en producción hacen fallar el proceso en el
arranque, no en tiempo de request.

## Seguridad

- Ningún secreto versionado: `.env` está en `.gitignore`; `gitleaks` corre en CI.
- Las rutas internas exigen `X-Admin-Api-Key`, comparada con `hmac.compare_digest`.
  Verificado en producción: sin credencial devuelven 401.
- El contenido web se inserta en el prompt delimitado y marcado explícitamente
  como dato, nunca como instrucción (defensa contra prompt injection).
- Antes de seguir la URL de origen de un evento se rechazan destinos privados,
  loopback, link-local, reservados y multicast (defensa contra SSRF).
- No hay cuentas de usuario final ni datos personales: solo información pública
  de eventos.

Pendientes conocidos: no hay limitación de tasa, `/docs` está abierto en
producción, la credencial administrativa se guarda en `localStorage` del
navegador, el tráfico va sin cifrar y el cliente HTTP escribe las claves de los
geocodificadores en los logs. Todos están documentados en el informe de entrega.

## Limitaciones conocidas

- **Sin HTTPS**: el certificado TLS no fue emitido para los dominios del proyecto.
- **`GET /api/v1/categories` devuelve 500**: la consulta combina `DISTINCT` con
  un ordenamiento no incluido en la proyección. No afecta a la interfaz, que
  deriva las categorías del listado de eventos.
- **La cola de revisión no se puede resolver**: `POST /reviews/{id}/approve` y
  `/reject` devuelven 501, declarados y no implementados.
- **Sin OCR y sin Facebook**: ambos previstos en el diseño y deshabilitados por
  configuración. Los eventos publicados solo como imagen no se detectan.
- **El modelo no corre localmente**: el cliente es Ollama, pero `minimax-m3` se
  ejecuta en infraestructura remota. Es un esquema híbrido.
- **La fusión de duplicados es parcial**: completa campos vacíos, pero no aplica
  la regla de preferir el dato de la fuente más confiable campo por campo.

## Estructura del repositorio

```text
eventradar/
├── backend/
│   ├── app/
│   │   ├── agents/        # los 6 agentes implementados + el contrato del 7.º
│   │   ├── api/           # /health, /ready y /api/v1
│   │   ├── domain/        # entidades, enums y errores compartidos
│   │   ├── models/        # modelos Tortoise (11 tablas)
│   │   ├── repositories/
│   │   ├── services/      # llm/, geocoding/, matching/, scoring/, sources/
│   │   ├── sources/       # adaptadores RSS, Scrapy, Playwright, Facebook
│   │   ├── scheduler/     # APScheduler + watchdog
│   │   └── security/      # autenticación de las rutas internas
│   ├── migrations/
│   ├── scripts/
│   └── tests/             # unit, integration, e2e, smoke
├── frontend/src/          # api, components, hooks, pages, styles, types
├── data/                  # catálogo de fuentes, catálogo geográfico, datasets
├── db/                    # utilidades SQL
├── deploy/nginx/
├── report/                # documentación de la entrega (no forma parte del sistema)
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

## Contribuir

Ramas cortas y pull request contra `develop`. Antes de abrir el PR:

1. `ruff check . && ruff format --check . && mypy app && pytest` en `backend/`
2. `npm run lint && npm run typecheck && npm test && npm run build` en `frontend/`
3. Confirmar que no se versionan secretos

## Equipo

- **Paulo Cabrera** — Desarrollador Fullstack
- **Emiliano Domínguez** — Desarrollador Fullstack

Proyecto final de *Inteligencia Artificial Aplicada a Organizaciones* — UTN FRBA.
