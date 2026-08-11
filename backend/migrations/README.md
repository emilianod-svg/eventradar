# Migraciones (Aerich)

Esta carpeta la administra [Aerich](https://github.com/tortoise/aerich). No
se generó todavía la migración inicial porque este sandbox de inicialización
no tiene acceso a una instancia de PostgreSQL ni a internet para instalar
dependencias (ver informe de inicialización, sección "Validaciones
ejecutadas").

## Generar la migración inicial (una sola vez, con Postgres corriendo)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # o el gestor que prefieran
pip install -e ".[dev]"
cp ../.env.example ../.env   # completar POSTGRES_* / DATABASE_URL reales
aerich init -t app.config.TORTOISE_ORM
aerich init-db
```

`aerich init-db` crea la tabla de control `aerich` y la primera migración en
`migrations/models/`. Los cambios posteriores a los modelos se versionan con:

```bash
aerich migrate --name "descripcion_del_cambio"
aerich upgrade
```

No se debe editar a mano el contenido generado en `migrations/models/`.
