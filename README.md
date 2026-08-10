# EventRadar

Sistema inteligente de centralización y recomendación de eventos locales —
**Posadas, Misiones**. Este repositorio contiene la base inicial del MVP:
backend en FastAPI, frontend en Vite + React + TypeScript, y la
infraestructura Docker/CI necesaria para desarrollarlo y desplegarlo.

> La fuente de verdad funcional y arquitectónica completa es
> [`EventRadar_Plan_Completo-v1.md`](./EventRadar_Plan_Completo-v1.md). Este
> README resume lo operativo; ante cualquier duda de alcance o reglas de
> negocio, el plan tiene precedencia.

## Estado de esta inicialización

Este repositorio fue inicializado siguiendo el
[`PROMPT_INICIALIZACION_EVENTRADAR.md`](./PROMPT_INICIALIZACION_EVENTRADAR.md).
**No implementa todavía la lógica de scraping, LLM, OCR, geocodificación ni
deduplicación** — eso es intencional. Lo que sí existe y funciona:

- Backend FastAPI con configuración tipada, `/health`, `/ready`,
  `/api/v1/events`, `/api/v1/categories` y `/api/v1/internal/sources`
  (CRUD real contra PostgreSQL).
- Modelos Tortoise ORM completos del modelo de datos del plan (sección 11).
- Contratos tipados de los 7 agentes (sección 8) y de los servicios externos
  (LLM, OCR, geocoding, matching, scoring), todos como *stubs* que fallan
  explícitamente en vez de simular resultados.
- Frontend con pantalla inicial, chequeo real de `/health`, estados
  loading/error/vacío y accesibilidad base.
- Docker, Docker Compose (dev y prod) y CI en GitHub Actions.

Ver el informe de inicialización (compartido junto con este README) para el
detalle de validaciones ejecutadas, pendientes P0/P1/P2 y recursos externos
que el equipo debe conseguir.

## 1. Propósito y alcance P0

Convertir publicaciones públicas heterogéneas (webs estáticas, Facebook) en
eventos estructurados, geolocalizados y consultables vía API/cards, con
trazabilidad completa y aprendizaje de confiabilidad por fuente. El alcance
P0 completo está detallado en la sección 4.1 del plan; en resumen: 5 fuentes
configuradas, al menos 3 procesadas por ciclo, extracción con LLM + OCR,
geocodificación con radio, deduplicación con RapidFuzz, persistencia
trazable, scheduler con lock único, API paginada y frontend de cards.

### Arquitectura resumida

Monolito modular: los agentes (Orquestador, Descubridor, Recolector,
Analizador, Clasificador Geográfico, Evaluador, Persistencia) son módulos de
`backend/app/agents/`, no microservicios. Las integraciones externas (LLM,
OCR, geocoding, fuentes web) están detrás de interfaces en
`backend/app/services/` y `backend/app/sources/`. Ver diagrama en la
sección 6 del plan.

## 2. Requisitos previos

- Python 3.11 o 3.12
- Node.js 20+
- Docker y Docker Compose v2 (para el flujo con contenedores)
- PostgreSQL 16 (si se corre el backend sin Docker)

## 3. Inicio rápido con Docker Compose

```bash
cp .env.example .env
# completar al menos POSTGRES_PASSWORD y ADMIN_API_KEY con valores propios
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- PostgreSQL: localhost:5432 (expuesto solo para debug local)

> Este comando no se pudo ejecutar en el entorno de inicialización porque no
> tiene Docker disponible. Ver el informe de inicialización, sección
> "Validaciones ejecutadas", para el detalle exacto de qué se validó y qué
> falta correr en una máquina con Docker.

## 4. Inicio local sin Docker

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp ../.env.example ../.env  # completar valores
# con PostgreSQL corriendo localmente y DATABASE_URL/.env apuntando a él:
aerich init -t app.config.TORTOISE_ORM   # una sola vez
aerich init-db                            # una sola vez
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install   # genera package-lock.json si no existe (ver pendientes)
npm run dev
```

El frontend lee `VITE_API_URL` desde el `.env` de la **raíz** del
repositorio (`vite.config.ts` tiene `envDir: ".."`), no desde
`frontend/.env`.

## 5. Migraciones y seed

Las migraciones se administran con Aerich (ver
[`backend/migrations/README.md`](./backend/migrations/README.md)). No se
generó la migración inicial en esta inicialización por falta de acceso a
PostgreSQL en el entorno de scaffolding; es el primer paso pendiente P0.

El seed de fuentes vive en [`data/seed_sources.json`](./data/seed_sources.json)
con las 5 fuentes decididas en el plan, `active: false` y `base_url: null`
hasta confirmar URLs reales (no se inventaron). Cargarlas vía
`POST /api/v1/internal/sources` una vez confirmadas. Ver
[`data/README.md`](./data/README.md) para los datasets de evaluación
todavía pendientes.

## 6. Comandos de lint, tests, type checking y build

### Backend (`cd backend`)

| Comando | Qué hace |
|---|---|
| `ruff check .` | Lint |
| `ruff format --check .` | Formato |
| `mypy app` | Type checking |
| `pytest` | Tests (unitarios + integración si `TEST_DATABASE_URL` está definida) |

### Frontend (`cd frontend`)

| Comando | Qué hace |
|---|---|
| `npm run lint` | ESLint |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Vitest |
| `npm run build` | Build de producción (incluye type checking) |

## 7. URLs y endpoints

| Entorno | Backend | Frontend |
|---|---|---|
| Local (sin Docker) | http://localhost:8000 | http://localhost:5173 |
| Docker Compose (dev) | http://localhost:8000 | http://localhost:5173 |
| Producción (pendiente) | https://eventradar.net.ar/api | https://eventradar.net.ar |

- `GET /health` — estado del proceso (no depende de la base).
- `GET /ready` — verifica PostgreSQL.
- `GET /api/v1/events`, `GET /api/v1/events/{id-or-slug}` — API pública.
- `GET /api/v1/categories` — categorías activas.
- `GET/POST/PATCH /api/v1/internal/*` — API interna, requiere header
  `X-Admin-Api-Key` con el valor de `ADMIN_API_KEY`.
- OpenAPI/Swagger autogenerado por FastAPI: `/docs` y `/openapi.json`
  (deshabilitar `/docs` en producción si el equipo lo decide así — no
  configurado explícitamente todavía).

## 8. Estructura de carpetas

```text
eventradar/
├── backend/            # FastAPI + Tortoise ORM + Aerich
│   ├── app/
│   │   ├── api/        # routers públicos (/health, /ready) e internos (/api/v1)
│   │   ├── agents/      # contratos de los 7 agentes del plan (stubs)
│   │   ├── domain/      # entidades, enums, errores compartidos
│   │   ├── models/      # modelos Tortoise (sección 11 del plan)
│   │   ├── repositories/
│   │   ├── services/    # llm/ocr/geocoding/matching/scoring (interfaces)
│   │   ├── sources/      # adaptadores scrapy/playwright/facebook (stubs)
│   │   ├── scheduler/    # APScheduler (deshabilitado por defecto)
│   │   └── security/     # autenticación admin de rutas internas
│   ├── migrations/
│   └── tests/
├── frontend/            # Vite + React + TypeScript
│   └── src/{api,components,hooks,pages,styles,types}
├── data/                # seed de fuentes y datasets de evaluación (pendientes)
├── deploy/nginx/        # reverse proxy de producción
├── .github/workflows/   # CI
├── docker-compose.yml       # desarrollo local
├── docker-compose.prod.yml  # base de producción (Donweb)
└── .env.example
```

## 9. Variables de entorno

Ver [`.env.example`](./.env.example) para el listado completo y comentado.
Agrupadas:

- **Aplicación:** `APP_NAME`, `ENVIRONMENT`, `LOG_LEVEL`.
- **PostgreSQL:** `POSTGRES_HOST/PORT/DB/USER/PASSWORD`, `DATABASE_URL`.
- **CORS y URLs públicas:** `CORS_ALLOWED_ORIGINS`, `BACKEND_PUBLIC_URL`,
  `FRONTEND_PUBLIC_URL`, `VITE_API_URL`.
- **Seguridad interna:** `ADMIN_API_KEY`.
- **Scheduler:** `TIMEZONE`, `SCHEDULER_ENABLED`, `SCHEDULER_CRON`.
- **Geografía:** `BASE_LATITUDE`, `BASE_LONGITUDE`, `SEARCH_RADIUS_KM`.
- **LLM:** `LLM_PROVIDER/MODEL/BASE_URL/API_KEY`, límites de tokens/timeout/reintentos.
- **OCR:** `OCR_ENABLED`, `GOOGLE_VISION_CREDENTIALS_JSON`.
- **Geocodificación:** `NOMINATIM_BASE_URL/USER_AGENT/CONTACT_EMAIL/RATE_LIMIT_SECONDS`.
- **IA:** `AI_MONTHLY_BUDGET_USD`.
- **Flags experimentales:** `ENABLE_EXPERIMENTAL_ADAPTERS`, `ENABLE_FACEBOOK_ADAPTER`.

Ninguna variable de este documento ni de `.env.example` es un secreto real.

## 10. Scheduler y prevención de duplicados

El scheduler (APScheduler, `backend/app/scheduler/`) está **deshabilitado
por defecto** (`SCHEDULER_ENABLED=false`) y su job real depende del
Orquestador, que todavía no está implementado. Cuando se implemente, debe
correr como una única instancia activa (proceso separado o garantía
equivalente — sección 19.2 del plan), nunca en cada worker de FastAPI, y
adquirir un lock antes de iniciar un ciclo (sección 13). La prevención de
duplicados de contenido usa el hash SHA-256 en `raw_contents` (único por
fuente); la deduplicación de eventos usa RapidFuzz + reglas de fecha/lugar
(sección 10 del plan) — ambas piezas son contratos en esta inicialización,
sin lógica implementada todavía.

## 11. Decisiones abiertas

- **Llama:** proveedor y modelo exactos sin definir (sección 3.1 del plan).
  El cliente está detrás de `app/services/llm/base.py` para poder cambiar
  de proveedor sin tocar el Agente Analizador.
- **Facebook:** no es una fuente garantizada hasta una prueba técnica real;
  el adaptador (`app/sources/facebook_adapter.py`) está deshabilitado por
  `ENABLE_FACEBOOK_ADAPTER=false` hasta cerrar estrategia (sección 3.2).
- **Donweb:** sin acceso SSH, plan ni datos de servidor confirmados. El
  `docker-compose.prod.yml` y `deploy/nginx/` son una base, no un despliegue
  probado.

## 12. Estrategia CI/CD

`.github/workflows/ci.yml` corre en cada PR y push a `main`: lint/type
checking/tests de backend con PostgreSQL como service container,
lint/typecheck/tests/build de frontend, build (sin push) de ambas imágenes
Docker, auditoría de dependencias (`pip-audit`, `npm audit`) y escaneo de
secretos (`gitleaks`). No hay CD configurado: falta información de
credenciales/registry/Donweb (ver informe de inicialización, checklist de
recursos). Cuando el equipo la tenga, se debe agregar un workflow de
despliegue manual/aprobado, no automático sin revisión.

## 13. Troubleshooting básico

| Síntoma | Causa probable | Acción |
|---|---|---|
| `/ready` responde `degraded` | PostgreSQL no accesible | Verificar `DATABASE_URL`/`POSTGRES_*` y que el contenedor/servicio esté arriba |
| `ConfigurationError: ADMIN_API_KEY` | Falta la variable | Definir `ADMIN_API_KEY` en `.env` |
| `ExternalServiceNotConfiguredError` en agentes | LLM/OCR/Nominatim/Facebook sin configurar | Esperado en esta inicialización; completar credenciales cuando el equipo las tenga |
| Frontend no encuentra `VITE_API_URL` | `.env` no copiado o `envDir` incorrecto | Confirmar que `.env` existe en la raíz del repo, no en `frontend/` |
| `npm ci` falla en CI | Falta `package-lock.json` versionado | Correr `npm install` localmente una vez y commitear el lockfile (pendiente P0) |

## 14. Seguridad y manejo de secretos

- Ningún secreto se versiona; `.env` está en `.gitignore` y `.claudeignore`.
- Rutas internas requieren `X-Admin-Api-Key` (`app/security/admin_auth.py`);
  fallan explícitamente si `ADMIN_API_KEY` no está configurada.
- CORS restringido por configuración; se rechaza `*` en `ENVIRONMENT=production`.
- Los adaptadores externos (LLM, OCR, geocoding, fuentes) fallan de forma
  explícita si no tienen credenciales, en vez de responder silenciosamente.
- Pendiente (fuera de alcance de esta inicialización): rate limiting real de
  endpoints administrativos, sanitización de contenido externo, protección
  SSRF en el Recolector — todos mencionados en la sección 16 del plan y a
  implementar junto con los agentes correspondientes.

## 15. Cómo contribuir y Definition of Done

Trunk-based development sobre `main` (sección 2.2 del plan). Antes de abrir
un PR:

1. `ruff check . && ruff format --check . && mypy app && pytest` en `backend/`.
2. `npm run lint && npm run typecheck && npm test && npm run build` en `frontend/`.
3. Confirmar que no se versionan secretos (`git diff --cached` + revisión manual).

Una tarea está terminada (sección 21 del plan) cuando cumple su criterio de
aceptación, tiene tests adecuados, no contiene secretos, pasa CI, tiene logs
comprensibles, su configuración está documentada y no deja `TODO` que
bloqueen el flujo P0.
