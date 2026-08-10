# Prompt para inicializar EventRadar

Actuá como agente principal de ingeniería de software y DevOps responsable de inicializar el repositorio de **EventRadar**. Tu trabajo debe basarse en el documento `EventRadar_Plan_Completo-v1 (1).md`, que es la fuente de verdad funcional y arquitectónica.

## Objetivo

Dejar una base ejecutable, documentada, segura y escalable del MVP de EventRadar, respetando la arquitectura propuesta:

- Backend: Python, FastAPI, Tortoise ORM, Aerich y PostgreSQL.
- Frontend: Vite, React y TypeScript.
- Arquitectura: monolito modular; los agentes son módulos de aplicación, no microservicios.
- Servicios externos encapsulados mediante interfaces/adaptadores.
- Backend y frontend dockerizados por separado.
- PostgreSQL y proxy web integrados mediante Docker Compose cuando corresponda.
- CI/CD inicial mediante GitHub Actions.

No implementes todavía toda la lógica de scraping, LLM, OCR, geocodificación o deduplicación. Inicializá contratos, módulos, configuración, stubs explícitos y una primera vertical técnica ejecutable, sin simular como terminadas integraciones que aún requieren credenciales o decisiones del equipo.

## Reglas de trabajo obligatorias

1. Antes de modificar archivos, inspeccioná completamente:
   - el documento del plan;
   - el estado del repositorio y su rama actual;
   - archivos y código preexistentes;
   - cambios locales sin confirmar;
   - remotos configurados;
   - instrucciones `AGENTS.md`, `CLAUDE.md` u otras equivalentes.
2. No sobrescribas ni descartes cambios existentes del equipo.
3. Presentá primero un diagnóstico breve y un plan de ejecución. Podés continuar con cambios locales reversibles, pero detenete si encontrás decisiones incompatibles, secretos, trabajo ajeno que sería sobrescrito o una arquitectura ya inicializada distinta del plan.
4. Priorizá una base simple, funcional y ampliable. No agregues Kubernetes, colas, Redis, microservicios ni infraestructura no solicitada.
5. No incluyas secretos, tokens, claves ni credenciales reales.
6. Fijá rangos/versiones compatibles y documentá las decisiones. No inventes credenciales ni URLs de proveedores.
7. Ejecutá y registrá las validaciones reales disponibles. No afirmes que algo funciona si no fue probado.
8. No hagas `git commit`, `git push`, creación de tags, releases, despliegues ni cambios remotos hasta completar la entrega local, mostrar el resultado y recibir aprobación explícita del usuario.
9. Nunca fuerces el push ni reescribas historia. Usá un commit convencional y un push normal sobre la rama autorizada.

## Fase 1 — Diagnóstico y decisiones

Verificá y reportá:

- si el repositorio está vacío o parcialmente inicializado;
- rama activa, remoto y estado de Git;
- herramientas disponibles y versiones de Python, Node, Docker y Compose;
- contradicciones entre el plan y el estado real;
- decisiones todavía abiertas que no bloquean el scaffolding;
- cualquier bloqueo que requiera intervención humana.

Si el repositorio no tiene nombre o remoto configurado, no inventes uno: dejá el comando exacto sugerido y solicitá el dato correspondiente antes del push.

## Fase 2 — Estructura del repositorio

Creá o completá, adaptándote a lo que ya exista, esta estructura mínima:

```text
eventradar/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── domain/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── services/
│   │   │   ├── llm/
│   │   │   ├── ocr/
│   │   │   ├── geocoding/
│   │   │   ├── matching/
│   │   │   └── scoring/
│   │   ├── sources/
│   │   ├── scheduler/
│   │   ├── security/
│   │   ├── config.py
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   ├── aerich.ini
│   ├── Dockerfile
│   └── .dockerignore
├── frontend/
│   ├── src/
│   ├── public/placeholders/
│   ├── package.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── .dockerignore
├── data/
├── deploy/nginx/
├── .github/workflows/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── .claudeignore
└── README.md
```

No crees carpetas vacías innecesarias: agregá archivos mínimos útiles o `.gitkeep` únicamente donde exista una razón documentada.

## Fase 3 — Backend mínimo ejecutable

Implementá una base de FastAPI que incluya:

- configuración tipada por variables de entorno;
- inicialización de Tortoise ORM compatible con Aerich;
- configuración CORS por entorno, sin `*` como valor productivo predeterminado;
- `GET /health`, que compruebe el proceso;
- `GET /ready`, que compruebe al menos PostgreSQL;
- prefijo `/api/v1` preparado;
- manejo común de errores con `code`, `message`, `details` y `correlation_id`;
- logging estructurado básico;
- contrato genérico tipado para los agentes y módulos iniciales coherentes con el plan;
- tests mínimos para health/readiness y configuración;
- comandos de formato, lint, type checking y tests.

Los clientes de Llama, Google Vision, Nominatim y fuentes web deben quedar detrás de interfaces propias. Si aún no están configurados, deben fallar de manera explícita y entendible, no silenciosamente.

## Fase 4 — Frontend mínimo ejecutable

Inicializá Vite + React + TypeScript con:

- estructura de `api`, `components`, `hooks`, `pages`, `styles` y `types`;
- configuración de URL del backend mediante variable de entorno de Vite;
- pantalla inicial responsive de EventRadar;
- estados básicos loading, error y vacío;
- consumo real de `/health` o de un endpoint público mínimo disponible;
- accesibilidad base;
- lint, type checking, build y tests mínimos si la configuración elegida los contempla.

No inventes eventos productivos. Si necesitás datos de demostración, marcá claramente fixtures o mocks solo para desarrollo/test.

## Fase 5 — Docker y entornos

Dockerizá backend y frontend por separado:

- imágenes reproducibles y livianas;
- ejecución con usuario no root cuando sea razonable;
- builds multi-stage donde aporten valor;
- healthchecks;
- `.dockerignore` específicos;
- sin secretos dentro de las imágenes;
- frontend productivo servido como estáticos mediante Nginx o una solución equivalente coherente con el plan.

Prepará:

1. `docker-compose.yml` para desarrollo/integración local.
2. `docker-compose.prod.yml` para una base de producción en Donweb.
3. Servicios separados para `backend`, `frontend` y `postgres`.
4. Un único scheduler activo: separalo como proceso/servicio si esa decisión evita que se ejecute en cada worker de FastAPI.
5. Volumen persistente para PostgreSQL, redes internas y exposición mínima de puertos.
6. Estrategia de migraciones documentada y segura.

Usá variables diferenciadas y documentadas, como mínimo para:

- nombre/entorno de la aplicación;
- host, puerto, base, usuario y contraseña de PostgreSQL;
- URL de base de datos;
- origen permitido de CORS;
- URL pública del backend y variable Vite correspondiente;
- credencial administrativa interna;
- zona horaria y cron del scheduler;
- radio y coordenadas base de Posadas;
- proveedor/modelo/base URL/API key del LLM;
- credenciales de Google Vision;
- identificación/contacto y rate limit para Nominatim;
- límites de tokens, timeouts, reintentos y presupuesto mensual de IA;
- flags para activar o desactivar OCR, scheduler y adaptadores experimentales.

En `.env.example` colocá únicamente nombres y valores de ejemplo no sensibles, con comentarios claros. Validá al inicio las variables obligatorias.

## Fase 6 — Archivos de exclusión

Creá un `.gitignore` apropiado para Python, Node/Vite, IDEs, SO, cobertura, caches, entornos virtuales, builds, logs, archivos `.env`, credenciales y datos locales. Conservá `.env.example`.

Creá `.claudeignore` para evitar enviar al contexto del agente:

- dependencias y entornos virtuales;
- builds y cobertura;
- caches, logs y temporales;
- secretos y archivos de entorno;
- dumps, volúmenes y datasets pesados;
- artefactos binarios generados.

No ignores código fuente, migraciones, fixtures pequeños necesarios, documentación ni archivos de lock.

## Fase 7 — GitHub Actions: CI y base de CD

Creá al menos `.github/workflows/ci.yml` con ejecución en pull requests y pushes a `main`:

- backend: instalación reproducible, formato/lint, type checking y tests;
- PostgreSQL como service container para integración cuando corresponda;
- frontend: instalación con lockfile, lint, type checking, tests configurados y build;
- validación de Dockerfiles o build de imágenes;
- detección básica de secretos y auditoría de dependencias;
- cache seguro de dependencias;
- permisos mínimos y cancelación de ejecuciones obsoletas.

Prepará CD solamente si existe información suficiente del destino. Si faltan credenciales, registry o datos de Donweb, dejá un workflow manual/documentado o una plantilla deshabilitada que no finja desplegar. Indicá exactamente qué GitHub Secrets/Environments deberá crear el equipo. No ejecutes despliegues.

## Fase 8 — README operativo

El `README.md` debe permitir que una persona nueva use y comprenda el proyecto. Incluí:

- propósito, alcance P0 y arquitectura resumida;
- requisitos previos;
- inicio rápido con Docker Compose;
- inicio local de backend y frontend por separado;
- copia y configuración de `.env.example`;
- migraciones y seed;
- comandos de lint, tests, type checking y build;
- URLs, endpoints health/readiness y OpenAPI;
- estructura de carpetas;
- variables de entorno agrupadas, sin secretos;
- funcionamiento del scheduler y prevención de duplicados;
- decisiones abiertas: Llama, Facebook/fuentes sustitutas y Donweb;
- estrategia CI/CD;
- troubleshooting básico;
- seguridad y manejo de secretos;
- criterios para contribuir y Definition of Done.

## Fase 9 — Validación integral

Ejecutá todo lo que el entorno permita:

- instalación reproducible de dependencias;
- formato/lint y type checking del backend;
- tests del backend;
- lint, tests/type checking y build del frontend;
- renderizado o validación de Docker Compose;
- build de imágenes;
- arranque de servicios;
- verificación HTTP de `/health`, `/ready` y frontend;
- comprobación de que no se versionen secretos.

Si Docker u otra dependencia no está disponible, no lo ocultes: informá el comando exacto que debe ejecutar el equipo. Corregí los errores atribuibles a tus cambios antes de presentar la entrega.

## Fase 10 — Informe final antes de Git

Antes de cualquier commit o push, entregá un informe detallado y ordenado con:

1. **Resumen de lo creado y decisiones adoptadas.**
2. **Árbol de archivos relevante.**
3. **Validaciones ejecutadas**, indicando comando y resultado.
4. **Pendientes y riesgos**, diferenciando bloqueo, P0, P1 y P2.
5. **Recursos externos que deben obtener los desarrolladores**, indicando para cada uno:
   - responsable sugerido;
   - enlace o consola donde se obtiene, si está confirmado;
   - credencial/configuración necesaria;
   - costo o límite conocido;
   - dónde configurarlo localmente y en GitHub/Donweb;
   - cómo verificarlo sin exponer secretos.
6. **Checklist de recursos**, como mínimo:
   - repositorio GitHub, permisos y protección de `main`;
   - proveedor, cuenta, modelo y API key para Llama;
   - proyecto de Google Cloud con Vision API, facturación y credencial segura;
   - política de uso de Nominatim y un `User-Agent`/contacto válido;
   - acceso autorizado a fuentes y decisión sobre Facebook;
   - dominio `eventradar.net.ar`, DNS y TLS;
   - servidor/plan Donweb, acceso SSH, firewall, volúmenes y backup;
   - registry de imágenes si se utiliza;
   - GitHub Secrets y Environments requeridos.
7. **Plan de trabajo para los próximos días**, actualizado desde la fecha real de ejecución hasta el 20/08/2026. Proponé tareas concretas, pequeñas y verificables para Paulo Cabrera y Emiliano Dominguez, pero marcá como “asignación propuesta” cualquier reparto no confirmado. Incluí dependencia, criterio de aceptación y prioridad de cada tarea.
8. **Comandos exactos de uso local y despliegue**, sin secretos.
9. **Estado Git propuesto**: archivos a confirmar, rama, mensaje de commit y remoto/destino del push.

Al distribuir tareas, mantené la ruta crítica del plan: primero una vertical end-to-end con una fuente estática; después nuevas fuentes, Llama, OCR, geocodificación, deduplicación, aprendizaje, scheduler y endurecimiento productivo.

## Fase 11 — Aprobación, commit y push

Después del informe:

1. Detenete y solicitá aprobación explícita.
2. Mostrá el mensaje de commit propuesto, por ejemplo: `chore: initialize EventRadar project foundation`.
3. Solo tras recibir aprobación, volvé a revisar `git status` y `git diff`.
4. Confirmá únicamente archivos pertenecientes a esta inicialización.
5. Ejecutá los checks finales aplicables.
6. Creá el commit sin desactivar hooks.
7. Hacé push normal a la rama/remoto autorizados, sin `--force`.
8. Informá hash del commit, rama, remoto y resultado del push.

Si la rama es `main` y está protegida o el flujo requiere pull request, creá o proponé una rama `chore/initialize-eventradar` y seguí el mecanismo autorizado. No alteres reglas de protección para evitar controles.

## Criterios de aceptación de esta inicialización

La tarea se considera terminada únicamente si:

- backend y frontend pueden instalarse y ejecutarse por separado;
- el stack puede iniciarse con Docker Compose o quedan documentadas limitaciones reales del entorno;
- `/health`, `/ready` y el frontend tienen una validación verificable;
- PostgreSQL y migraciones están configurados;
- no hay secretos versionados;
- `.gitignore`, `.claudeignore`, `.env.example`, Dockerfiles, Compose, CI y README son coherentes entre sí;
- las integraciones externas están desacopladas y sus faltantes están documentados;
- el informe final contiene recursos externos y tareas nominales propuestas;
- el commit y push ocurren solamente después de aprobación explícita.

Cuando el plan y el repositorio entren en conflicto, explicá la diferencia y pedí decisión si cambia alcance, arquitectura, costos o seguridad. No completes huecos importantes inventando supuestos.
