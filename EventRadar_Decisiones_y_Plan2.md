# 📋 EventRadar — Decisiones Previas y Plan de Desarrollo

**Documento de definiciones para iniciar el desarrollo del MVP**
**Equipo:** Paulo Cabrera · Emiliano Dominguez
**Fecha:** Agosto 2026

---

## 1. Decisiones Estratégicas (Definir antes de escribir código)

### 1.1 🎯 Alcance del MVP

| # | Pregunta | Opciones | Nuestra decisión |
|---|----------|----------|:----------------:|
| 1 | **¿Cuál es la ciudad/zona objetivo del MVP?** | La Plata / CABA / Zona Norte GBA / Otra | Posadas, Misiones |
| 2 | **¿Cuántas fuentes iniciales vamos a configurar?** | 5-10 / 10-20 / +20 | 5 |
| 3 | **¿Qué tipos de fuentes priorizamos para el MVP?** | Solo web estática / Incluir redes sociales / Incluir APIs de ticketing | webs estáticas, facebook |
| 4 | **¿El MVP incluye análisis de imágenes (flyers/banners)?** | Sí desde el inicio / No, solo texto / Fase posterior | si |
| 5 | **¿El frontend del MVP es solo cards o incluye mapa?** | Solo cards / Cards + Mapa / Cards + Mapa + Detalle | solo cards |
| 6 | **¿Implementamos el módulo de administración en el MVP?** | Sí / No, solo endpoints internos | solo endpoints internos |
| 7 | **¿Cuántas categorías de eventos soportamos inicialmente?** | Las 7 del doc (Concierto/Feria/Cine/Deporte/Gastronomía/Municipal/Otro) / Menos | no está limitado |

### 1.2 🛠️ Stack Tecnológico

| # | Pregunta | Opciones | Nuestra decisión |
|---|----------|----------|:----------------:|
| 8 | **¿Qué LLM usamos para NLP y clasificación?** | OpenAI GPT-4o / Claude API / Gemini / Open source (Llama) | llama |
| 9 | **¿Presupuesto mensual estimado para APIs de IA?** | $0 (solo gratis) / hasta $20 USD / hasta $50 USD / más | 20 USD |
| 10 | **¿Framework de orquestación de agentes?** | LangGraph / CrewAI / Autogen / Custom (sin framework) | custom |
| 11 | **¿Base de datos?** | PostgreSQL / SQLite (dev) + PostgreSQL (prod) / Supabase | postgresql |
| 12 | **¿ORM?** | SQLAlchemy / Tortoise ORM / Raw SQL | _________________ |
| 13 | **¿API de geocodificación?** | Google Maps (paga, precisa) / Nominatim-OSM (gratis, menos precisa) / Ambas con fallback | _________________ |
| 14 | **¿Librería de scraping principal?** | Scrapy / BeautifulSoup + requests / Playwright (headless browser) / Combinación | _________________ |
| 15 | **¿Framework frontend?** | Next.js (SSR, mejor SEO) / Vite + React (SPA, más simple) / Astro | _________________ |
| 16 | **¿Librería de mapas?** | Leaflet (gratis) / Mapbox GL (freemium, más lindo) / Google Maps JS | _________________ |
| 17 | **¿Scheduler para ciclos automáticos?** | APScheduler (simple) / Celery + Redis (robusto) / Cron del sistema | _________________ |

### 1.3 🚀 Infraestructura y Deploy

| # | Pregunta | Opciones | Nuestra decisión |
|---|----------|----------|:----------------:|
| 18 | **¿Dónde deployamos el MVP?** | Railway / Render / Fly.io / VPS (DigitalOcean/Hetzner) / Local solamente | _________________ |
| 19 | **¿Presupuesto mensual para hosting?** | $0 (free tiers) / hasta $10 USD / hasta $25 USD | _________________ |
| 20 | **¿Usamos Docker desde el inicio?** | Sí / Solo en producción / No | _________________ |
| 21 | **¿Dominio propio?** | Sí (¿cuál?) / Subdominio del hosting (ej: eventradar.railway.app) | _________________ |

### 1.4 👥 Organización del Equipo

| # | Pregunta | Opciones | Nuestra decisión |
|---|----------|----------|:----------------:|
| 22 | **¿Cómo nos dividimos el trabajo?** | Por capa (uno backend, otro frontend) / Por feature / Pair programming | _________________ |
| 23 | **¿Horas semanales dedicadas al proyecto?** | 5-10hs / 10-20hs / +20hs | _________________ |
| 24 | **¿Fecha límite para el MVP funcional?** | ___ / ___ / 2026 | _________________ |
| 25 | **¿Herramienta de gestión de tareas?** | GitHub Projects / Trello / Notion / Ninguna | _________________ |
| 26 | **¿Estrategia de branching en Git?** | GitFlow / Trunk-based / Feature branches simples | _________________ |

---

## 2. Verificaciones Técnicas (Validar antes de codear)

### 2.1 Fuentes de Datos — Viabilidad de Scraping

> [!IMPORTANT]
> Antes de implementar el scraper, verificar manualmente cada fuente candidata.

Para cada fuente de la lista inicial, completar:

| Fuente | URL | ¿Tiene robots.txt que bloquea? | ¿Es contenido estático o dinámico (JS)? | ¿Los eventos están en texto o en imágenes? | ¿Tiene estructura predecible (clases CSS, JSON-LD)? | ¿Con qué frecuencia publican? | Viable para MVP |
|--------|-----|:------------------------------:|:----------------------------------------:|:-------------------------------------------:|:----------------------------------------------------:|:-----------------------------:|:---------------:|
| Fuente 1 | | ☐ Sí / ☐ No | ☐ Estático / ☐ Dinámico | ☐ Texto / ☐ Imagen / ☐ Ambos | ☐ Sí / ☐ No | | ☐ Sí / ☐ No |
| Fuente 2 | | ☐ Sí / ☐ No | ☐ Estático / ☐ Dinámico | ☐ Texto / ☐ Imagen / ☐ Ambos | ☐ Sí / ☐ No | | ☐ Sí / ☐ No |
| Fuente 3 | | ☐ Sí / ☐ No | ☐ Estático / ☐ Dinámico | ☐ Texto / ☐ Imagen / ☐ Ambos | ☐ Sí / ☐ No | | ☐ Sí / ☐ No |
| Fuente 4 | | ☐ Sí / ☐ No | ☐ Estático / ☐ Dinámico | ☐ Texto / ☐ Imagen / ☐ Ambos | ☐ Sí / ☐ No | | ☐ Sí / ☐ No |
| Fuente 5 | | ☐ Sí / ☐ No | ☐ Estático / ☐ Dinámico | ☐ Texto / ☐ Imagen / ☐ Ambos | ☐ Sí / ☐ No | | ☐ Sí / ☐ No |

**Acciones:**
- [ ] Elegir la ciudad objetivo y listar 10-15 fuentes candidatas
- [ ] Visitar cada fuente y completar la tabla de arriba
- [ ] Identificar al menos 5 fuentes viables para el MVP
- [ ] Verificar si alguna fuente tiene API pública (Eventbrite, Ticketek, etc.)

### 2.2 APIs Externas — Acceso y Costos

| API / Servicio | ¿Necesita API key? | ¿Tiene free tier? | Límite free tier | Costo estimado MVP | ¿Ya tenemos la key? |
|---------------|:-------------------:|:------------------:|:----------------:|:-------------------:|:--------------------:|
| LLM (OpenAI / Claude / Gemini) | Sí | Varía | Varía | ~$10-30/mes | ☐ |
| Google Maps Geocoding | Sí | Sí | $200 USD/mes crédito | Probablemente $0 | ☐ |
| Nominatim (OSM) | No | Sí (gratis) | 1 req/seg | $0 | ✅ |
| Google Vision API (OCR) | Sí | Sí | 1000 req/mes | Probablemente $0 | ☐ |
| Mapbox (frontend) | Sí | Sí | 50k cargas/mes | Probablemente $0 | ☐ |
| Leaflet (frontend) | No | Sí (gratis) | Sin límite | $0 | ✅ |

**Acciones:**
- [ ] Decidir qué LLM usar y crear la cuenta / obtener API key
- [ ] Decidir geocodificación (Google vs OSM) y obtener key si aplica
- [ ] Decidir si incluir OCR en MVP y obtener key si aplica
- [ ] Calcular costo mensual estimado total

### 2.3 Datos Históricos (Seed)

> [!NOTE]
> El documento menciona que ya cuentan con una base de datos inicial de eventos cargados manualmente. Verificar su estado.

- [ ] ¿En qué formato están los datos históricos? (CSV, JSON, Excel, otro)
- [ ] ¿Cuántos eventos tiene el dataset?
- [ ] ¿De qué zona/ciudad son?
- [ ] ¿Tienen todos los campos obligatorios (nombre, fecha, lugar, URL fuente)?
- [ ] ¿Están limpios o necesitan preprocesamiento?
- [ ] Convertir a formato `seed_events.json` estandarizado

---

## 3. Preguntas de Diseño del Sistema

### 3.1 Agente Analizador (NLP)

| # | Pregunta | Impacto |
|---|----------|---------|
| 27 | ¿Usamos un único prompt grande que haga discriminación + extracción, o dos pasos separados? | Costo vs. precisión |
| 28 | ¿Cuál es el threshold de confianza para aceptar un evento? (ej: ≥0.7, ≥0.8) | Más alto = menos eventos pero más precisos |
| 29 | ¿Qué hacemos con eventos que tienen confianza media (ej: 0.5-0.7)? | ¿Descartar? ¿Marcar para revisión manual? |
| 30 | ¿Cómo manejamos eventos recurrentes? (ej: "todos los sábados") | ¿Crear un evento por fecha? ¿Un solo registro? |

### 3.2 Agente Evaluador (Duplicados)

| # | Pregunta | Impacto |
|---|----------|---------|
| 31 | ¿Qué algoritmo de fuzzy matching usamos para detectar duplicados? | Levenshtein / cosine similarity / LLM |
| 32 | ¿Cuál es el threshold de similitud para considerar duplicado? | Muy bajo = pierde duplicados. Muy alto = falsos duplicados |
| 33 | Si un evento aparece en 2 fuentes, ¿nos quedamos con el de la fuente más confiable? | Lógica de merge |

### 3.3 Frontend y UX

| # | Pregunta | Impacto |
|---|----------|---------|
| 34 | ¿El usuario necesita crear cuenta/loguearse? | No en MVP (según doc), pero confirmar |
| 35 | ¿Mostramos el puntaje de calidad del evento al usuario? | Transparencia vs. complejidad visual |
| 36 | ¿Cómo manejamos eventos sin imagen? | Placeholder por categoría / Ícono genérico |
| 37 | ¿Idioma de la interfaz? | Solo español / Español + Inglés |

---

## 4. Plan de Desarrollo por Fases

### FASE 0 — Setup (~3 días)
```
☐ Crear repositorio GitHub (monorepo)
☐ Configurar estructura de carpetas
☐ docker-compose.yml (PostgreSQL + Redis)
☐ Inicializar backend (FastAPI + Alembic)
☐ Inicializar frontend (Next.js o Vite)
☐ .env.example con todas las keys necesarias
☐ CI básico (GitHub Actions: lint)
```
**✅ Done when:** `docker-compose up` levanta todo y `/health` devuelve 200.

### FASE 1 — Base de Datos y API (~5 días)
```
☐ Modelos SQLAlchemy: Eventos, Fuentes, Logs, Clasificaciones
☐ Migraciones Alembic
☐ Script de seed con datos históricos
☐ GET /events (con filtros: fecha, categoría, radio geográfico)
☐ GET /events/{id}
☐ GET /sources
```
**✅ Done when:** La API devuelve eventos seed filtrados correctamente.

### FASE 2 — Agentes Core (~3 semanas)
```
Sprint 2A - Scraper (~5 días)
  ☐ Clase base BaseAgent
  ☐ Scraper para páginas estáticas (BeautifulSoup)
  ☐ Scraper para páginas dinámicas (Playwright)
  ☐ Respeto de robots.txt
  ☐ Tests con páginas mockeadas

Sprint 2B - Analizador NLP (~5 días)
  ☐ Prompts para discriminación evento/no-evento
  ☐ Extracción de entidades → JSON estructurado
  ☐ (Opcional) OCR de flyers con LLM multimodal
  ☐ Scoring de confianza
  ☐ Validación contra datos seed

Sprint 2C - Clasificador Geográfico (~3 días)
  ☐ Integración API geocodificación
  ☐ Cálculo distancia (Haversine)
  ☐ Filtro por radio máximo
  ☐ Asignación de coordenadas y zona

Sprint 2D - Evaluador (~3 días)
  ☐ Validación campos obligatorios
  ☐ Detección de duplicados (fuzzy matching)
  ☐ Verificación URL fuente accesible
  ☐ Puntaje de calidad

Sprint 2E - Persistencia y Aprendizaje (~3 días)
  ☐ Persistir eventos validados
  ☐ Log de ejecución
  ☐ Actualizar índice confiabilidad fuentes
  ☐ Archivado automático de eventos pasados

Sprint 2F - Descubridor de Fuentes (~2 días)
  ☐ CRUD fuentes
  ☐ Priorización por confiabilidad
  ☐ Carga de lista inicial
```
**✅ Done when:** Cada agente funciona aisladamente con tests.

### FASE 3 — Orquestación (~1 semana)
```
☐ Agente Orquestador: coordina la secuencia completa
☐ Ciclo de 6 fases conectado end-to-end
☐ Scheduler (lunes y viernes)
☐ Endpoint manual: POST /admin/run-cycle
☐ Manejo de errores resiliente
☐ Test E2E: ciclo real con fuentes reales → eventos en DB
```
**✅ Done when:** Un ciclo completo scrapea ≥3 fuentes y persiste ≥1 evento válido.

### FASE 4 — Frontend (~2 semanas)
```
Sprint 4A - Vista Cards (~5 días)
  ☐ Design system (colores, tipografía, tokens)
  ☐ Layout responsivo
  ☐ FilterBar (ubicación, radio, fechas, categoría)
  ☐ EventCard component
  ☐ Grilla responsiva
  ☐ EventDetail modal/panel
  ☐ Conexión con API

Sprint 4B - Vista Mapa (~4 días)
  ☐ Mapa interactivo (Leaflet/Mapbox)
  ☐ Pins por categoría con colores
  ☐ Popup al clic
  ☐ Toggle Cards ↔ Mapa

Sprint 4C - Pulido (~3 días)
  ☐ Animaciones y transiciones
  ☐ Estados vacíos y de error
  ☐ SEO y meta tags
  ☐ Test responsive (mobile/tablet/desktop)
```

### FASE 5 — Deploy y Validación (~5 días)
```
☐ Dockerizar backend y frontend
☐ Deploy en plataforma elegida
☐ Variables de entorno en producción
☐ Ejecutar primer ciclo real
☐ Monitorear y ajustar
☐ README completo
```

---

## 5. Checklist Pre-Desarrollo

> [!CAUTION]
> No empezar a codear hasta que todos estos ítems estén resueltos.

### Decisiones obligatorias
- [ ] Ciudad/zona objetivo definida
- [ ] Lista de ≥5 fuentes viables verificadas
- [ ] LLM elegido y API key obtenida
- [ ] API de geocodificación elegida
- [ ] Plataforma de deploy elegida
- [ ] División de trabajo acordada (quién hace qué)
- [ ] Fecha límite del MVP acordada

### Cuentas y accesos
- [ ] Repositorio GitHub creado
- [ ] API key del LLM elegido
- [ ] API key de geocodificación (si aplica)
- [ ] Cuenta en plataforma de deploy (si aplica)

### Datos
- [ ] Dataset seed limpio en formato JSON
- [ ] Lista de fuentes iniciales con URLs verificadas

---

## 6. Riesgos Identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|:------------:|:-------:|------------|
| Las fuentes bloquean el scraping | Media | Alto | Rotar user-agents, respetar rate limits, tener fuentes de respaldo |
| El LLM clasifica mal (falsos positivos) | Alta al inicio | Medio | Threshold de confianza alto (≥0.8), validar contra seed |
| Costos de API superan el presupuesto | Media | Alto | Monitorear uso, cachear respuestas, evaluar modelos más baratos |
| Fuentes cambian su estructura HTML | Alta a mediano plazo | Medio | Usar selectores resilientes, alertas cuando falla una fuente |
| Geocodificación imprecisa en zonas suburbanas | Media | Bajo | Fallback manual, permitir corrección de coordenadas |
| El MVP no se completa a tiempo | Media | Alto | Priorizar: ciclo funcional E2E > features extras |

---

*Documento generado como guía de trabajo. Completar las columnas "Nuestra decisión" en reunión de equipo antes de iniciar la Fase 0.*
