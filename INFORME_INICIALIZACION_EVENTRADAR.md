# Informe de inicialización — EventRadar

**Fecha de ejecución:** 09/08/2026
**Rama de trabajo:** `chore/initialize-eventradar` (commit local `e0c3a79`, sin push)
**Fuente de verdad:** [`EventRadar_Plan_Completo-v1.md`](./EventRadar_Plan_Completo-v1.md)
**Prompt ejecutado:** [`PROMPT_INICIALIZACION_EVENTRADAR.md`](./PROMPT_INICIALIZACION_EVENTRADAR.md)

---

## 1. Resumen y decisiones adoptadas

Repo existente (no vacío): tenía solo los 3 documentos de plan + `.git` apuntando a `git@github.com:emilianod-svg/eventradar.git`, rama `main`. Nada de código previo, así que no hubo conflicto con trabajo del equipo.

**Hallazgo previo (no tocado):** los 3 `.md` de plan ya tenían cambios sin confirmar antes de empezar esta inicialización — pero al revisarlos con `git diff --ignore-all-space` son 0 bytes de diferencia real: es solo CRLF↔LF (probablemente por edición en Windows). No se modificaron ni se agregaron al commit de esta inicialización; quedan igual que se encontraron.

Se construyó la base siguiendo estrictamente la Fase 3 del prompt: **contratos y stubs explícitos**, no lógica de negocio. Decisiones no bloqueantes adoptadas para poder scaffoldear:

- Categorías sin tabla propia (se derivan de `events.category`), consistente con "taxonomía sin límite rígido" del plan.
- `/ready` devuelve 200 siempre, con `status: degraded` si Postgres falla (no 503) — la política final queda documentada como pendiente P1.
- Nominatim: falla explícito si falta `NOMINATIM_CONTACT_EMAIL`, aunque no requiere API key, porque su política de uso exige contacto identificable.
- `data/seed_sources.json`: 5 fuentes con `base_url: null` — **no se inventaron URLs**.

---

## 2. Árbol relevante

```
eventradar/
├── backend/app/{api,agents,domain,models,repositories,services,sources,scheduler,security}/  (58 .py, todos compilan)
├── backend/tests/{unit,integration,contract,e2e,fixtures}/
├── backend/{pyproject.toml,aerich.ini,Dockerfile,.dockerignore}
├── frontend/src/{api,components,hooks,pages,styles,types}/  (React+TS, Vitest)
├── frontend/{package.json,vite.config.ts,eslint.config.js,Dockerfile,nginx.conf}
├── data/{seed_sources.json,README.md}
├── deploy/nginx/eventradar.conf
├── .github/workflows/ci.yml
├── docker-compose.yml / docker-compose.prod.yml
├── .env.example / .gitignore / .claudeignore
└── README.md
```

108 archivos nuevos en total (132 rutas backend incluyendo carpetas, 28 frontend).

---

## 3. Validaciones ejecutadas

**Importante:** el sandbox usado para esta inicialización no tiene Docker ni acceso a red (pip/npm/apt y hasta SSH a github.com devuelven 403/Forbidden del proxy). Todo lo que sigue es lo único que se pudo validar de verdad:

| Comando | Resultado |
|---|---|
| `python3 -m py_compile` sobre los 62 `.py` de `backend/` | OK, compilan todos |
| Parseo JSON de `package.json`, `tsconfig*.json`, `seed_sources.json` | OK |
| Parseo YAML de `docker-compose.yml`, `docker-compose.prod.yml`, `ci.yml` | OK |
| `git check-ignore` sobre `.venv/`, `node_modules/`, `.env` de prueba | Ignorados correctamente |
| Grep de patrones de secretos sobre archivos nuevos | Sin coincidencias |
| `git push -u origin chore/initialize-eventradar` | Falló: sin red hacia GitHub desde este entorno (ver sección 9) |

**No ejecutado (requiere una máquina con Docker/red, por ejemplo la del equipo):** `pip install -e .[dev]`, `aerich init-db`, `pytest`, `ruff`, `mypy`, `npm install`, `npm run lint/typecheck/test/build`, `docker compose up`, verificación HTTP real de `/health` y `/ready`. Comandos exactos en la sección 8 y en el `README.md`.

---

## 4. Pendientes y riesgos

**Bloqueantes** (nadie puede avanzar sin esto):

- Proveedor/modelo Llama sin cerrar (sección 3.1 del plan).
- Estrategia Facebook sin validar técnicamente (sección 3.2) — adaptador deshabilitado por flag.
- URLs reales de las 5 fuentes sin confirmar.
- Migración inicial de Aerich sin generar (necesita Postgres corriendo).
- `package-lock.json` sin generar (sin acceso a npm registry en este entorno).

**P0:** implementar los 7 agentes (todos son stubs con `NotImplementedError`), dataset etiquetado de Posadas, ejecutar el checklist de Fase 9 en una máquina real.

**P1:** rate limiting real en endpoints admin, política definitiva de `/ready` (200 vs 503), placeholders por categoría (solo hay uno genérico), OCR y adaptador Playwright.

**P2:** todo lo listado en la sección 4.3 del plan (mapa, login, recomendaciones, etc.) — no tocado, correctamente fuera de alcance.

---

## 5-6. Recursos externos y checklist

| Recurso | Responsable sugerido | Dónde se obtiene | Costo/límite | Configurar en | Cómo verificar |
|---|---|---|---|---|---|
| GitHub: protección de `main` | Emiliano (owner del repo) | Settings del repo `emilianod-svg/eventradar` | Gratis | GitHub | Intentar push directo a `main` debe fallar |
| Proveedor Llama | Equipo (decisión abierta) | Según opción elegida (self-host, API gestionada, etc.) | Depende del proveedor | `.env` local + GitHub Secret en prod | `LLM_PROVIDER`/`LLM_MODEL` seteados; el cliente deja de devolver `external_service_not_configured` |
| Google Cloud + Vision API | Quien administre GCP del equipo | console.cloud.google.com | Vision tiene free tier limitado, luego por request | `GOOGLE_VISION_CREDENTIALS_JSON` (ruta a archivo, no el JSON en texto) | `OCR_ENABLED=true` + credencial válida sin exponer el contenido |
| Nominatim | Quien mantenga el backend | Sin registro, es público | Gratis, con rate limit de uso justo | `NOMINATIM_CONTACT_EMAIL`, `NOMINATIM_USER_AGENT` | El cliente deja de fallar por falta de contacto |
| Facebook (fuentes) | Equipo (decisión legal/técnica) | N/A hasta decidir estrategia | N/A | `ENABLE_FACEBOOK_ADAPTER` | Prueba técnica documentada antes de activar |
| Dominio `eventradar.net.ar` + DNS + TLS | Quien tenga el dominio | Registrador del dominio | Según registrador | `deploy/nginx/eventradar.conf` (bloque HTTPS comentado) | `curl -I https://eventradar.net.ar` responde con certificado válido |
| Servidor Donweb | Quien tenga la cuenta Donweb | Panel Donweb | Según plan contratado | `docker-compose.prod.yml` + SSH del servidor | Login SSH + `docker compose ps` con servicios `healthy` |
| Registry de imágenes (si aplica) | A definir | GHCR/Docker Hub | Gratis para repos públicos | GitHub Actions secret si se agrega CD | `docker pull` de la imagen sin credenciales expuestas en logs |
| GitHub Secrets/Environments | Emiliano | Settings → Secrets and variables | Gratis | — | Ejecutar un workflow que los use y confirmar que no aparecen en logs |

---

## 7. Plan de trabajo hasta el 20/08/2026 (asignación propuesta, sin confirmar)

| Fecha | Tarea | Propuesto para | Dependencia | Criterio de aceptación | Prioridad |
|---|---|---|---|---|---|
| 10/08 | Cerrar Llama, Facebook y URLs de fuentes | Ambos | — | Documento de decisiones actualizado | Bloqueante |
| 10/08 | Postgres + `aerich init-db` + migración inicial; validar `/health`/`/ready` reales | Emiliano | Postgres disponible | `/ready` responde `database: up` | P0 |
| 10/08 | `npm install`, commitear lockfile, validar pantalla inicial contra backend | Paulo | Backend corriendo | UI muestra "Backend conectado" | P0 |
| 11/08 | Primer adaptador Scrapy + fixture + test | Integrante A | URL confirmada | Test parsea fixture → `RawContentCandidate` | P0 |
| 11/08 | Prompt único NLP + schema Pydantic + mocks | Integrante B | Proveedor Llama cerrado | Test de `AnalyzerAgent` con LLM mockeado pasa | P0 |
| 12/08 | Segundo y tercer adaptador; idempotencia por hash | Integrante A | Adaptador 1 OK | 3 fuentes sin duplicar por hash | P0 |
| 13/08 | `AnalyzerAgent` real contra el LLM elegido | Integrante B | Cliente LLM implementado | Precisión ≥0.80 en casos de sección 18.3 | P0 |
| 14/08 | OCR + dataset Posadas (20/10/5/5) | Ambos | Cuenta GCP + dataset | Dataset versionado y usado en tests | P0 (con freeze si no hay E2E) |
| 15/08 | `GeoClassifierAgent` + `EvaluatorAgent` (RapidFuzz, umbrales 0.50/0.75/0.90) | A o B | Dataset de evaluación | Tests de duplicados pasan | P0 |
| 16/08 | `PersistenceAgent` + aprendizaje + `OrchestratorAgent` (ciclo E2E) | Backend owner | Agentes previos | Ciclo manual `COMPLETED`/`PARTIAL`, ≥5 eventos persistidos | P0 |
| 17/08 | APScheduler real, lock único, watchdog | Backend owner | Orquestador | Dos ciclos simultáneos no corren en paralelo | P0 |
| 18/08 | Frontend: grilla, filtros, detalle | Paulo | API con datos reales | Cards responsivas mobile/desktop | P0 |
| 19/08 | Docker Compose end-to-end, Donweb si hay acceso, pruebas de aceptación | Ambos | Credenciales Donweb (si no, se documenta la limitación) | `docker compose up` levanta los 3 servicios | P0 |
| 20/08 | Demo (guion sección 24), documentación final | Ambos | Todo lo anterior | Guion de 11 pasos sin caída global | P0 |

---

## 8. Comandos exactos

```bash
# Local sin Docker
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env   # completar valores
aerich init -t app.config.TORTOISE_ORM && aerich init-db
uvicorn app.main:app --reload

cd frontend && npm install && npm run dev

# Docker Compose (dev)
cp .env.example .env
docker compose up --build

# Producción (base, requiere DNS/TLS/credenciales reales primero)
docker compose -f docker-compose.prod.yml up --build -d
```

---

## 9. Estado Git

- **Rama:** se creó `chore/initialize-eventradar` (en vez de commitear directo a `main`) porque no se pudo confirmar si `main` tiene branch protection real en GitHub desde este entorno sin red.
- **Commit local:** `e0c3a79` — `chore: initialize EventRadar project foundation` — 108 archivos, 3489 inserciones. Incluye backend/, frontend/, data/, deploy/, .github/, docker-compose*.yml, .env.example, .gitignore, .claudeignore, README.md. **No incluye** los 3 `.md` de plan (diff de line-endings preexistente, ajeno a esta tarea).
- **Push:** falló. El sandbox de esta inicialización no tiene salida de red hacia GitHub (ni HTTPS ni SSH; el proxy devuelve 403/Forbidden). Como estos archivos ya están en la carpeta real `eventradar` del equipo, el push debe hacerse desde una máquina con acceso a internet:

  ```bash
  git push -u origin chore/initialize-eventradar
  ```

  Luego abrir un PR hacia `main` (o pushear directo si se confirma que no está protegida).

---

## Preguntas abiertas para el equipo

1. ¿Aprobás el commit tal como quedó (`e0c3a79` en `chore/initialize-eventradar`), o hay algo del scaffold que ajustar antes del push?
2. ¿`main` tiene branch protection en GitHub? Define si el flujo es PR o push directo.
3. ¿Qué hacemos con el diff de line-endings de los 3 `.md` de plan? (quedó sin tocar, a decisión del equipo si alguien lo normaliza aparte).
