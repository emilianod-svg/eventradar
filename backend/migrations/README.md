# Migraciones (Aerich)

Esta carpeta la administra [Aerich](https://github.com/tortoise/aerich). El
archivo `.aerichrc` (configuración de Aerich) está versionado en el
repositorio; la migración inicial se debe generar una sola vez cuando
PostgreSQL esté disponible.

## Configuración previa (IMPORTANTE)

Antes de ejecutar cualquier comando de Aerich, **debes asegurarte de que tu
PostgreSQL está corriendo y que `.aerichrc` contiene las credenciales
correctas**:

1. **Verifica tu PostgreSQL:**
   ```bash
   # La DB debe estar corriendo en localhost:5432 (o donde esté configurada)
   # Predeterminados en .env.example:
   # - Usuario: eventradar
   # - Contraseña: cambiar en .env
   # - Base de datos: eventradar
   ```

2. **Actualiza `.aerichrc` si tu configuración es diferente:**
   - Abre `backend/.aerichrc`
   - Cambia la `db_url` para que coincida con tu PostgreSQL
   - Formato: `postgres://usuario:contraseña@host:puerto/bd`
   - Ejemplo: `postgres://tuuser:tupass@localhost:5432/eventradar`

3. **O usa `DATABASE_URL` en `.env`:**
   - Si prefieres, edita `.env` y define `DATABASE_URL` completa
   - Pero recuerda actualizar también `.aerichrc` (Aerich lee este archivo
     directamente, no el `.env`)

## Generar la migración inicial (una sola vez, con Postgres corriendo)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env   # completar POSTGRES_* si es necesario
# ⚠️  Asegúrate de que .aerichrc tenga las credenciales correctas
aerich init-db
```

**Nota:** `aerich init` ya no es necesario — el archivo `.aerichrc` y la
configuración en `pyproject.toml` ya están presentes. Solo ejecuta
`aerich init-db` para crear la tabla de control `aerich` en PostgreSQL y
generar la primera migración en `migrations/models/`.

## Crear nuevas migraciones

Los cambios posteriores a los modelos en `app/models/` se versionan con:

```bash
aerich migrate --name "descripcion_del_cambio"
aerich upgrade
```

**No edites a mano el contenido generado en `migrations/models/`.** Aerich
genera estas migraciones automáticamente detectando los cambios en los modelos.

## Estructura

- `.aerichrc` — configuración de Aerich (versionada)
- `pyproject.toml` — sección `[tool.aerich]` con rutas y referencias
- `migrations/models/` — migraciones generadas automáticamente (no editar)
