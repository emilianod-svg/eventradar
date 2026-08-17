# Limpieza de base de datos

Este directorio contiene scripts para borrar los datos de la base local.

## `clean_database.sql`

El script hace `TRUNCATE` de todas las tablas del esquema `public` y reinicia las identidades.
También borra `aerich`, así que elimina el historial de migraciones.

Uso:

```bash
psql "$DATABASE_URL" -f db/clean_database.sql
```

Si solo queres vaciar datos de aplicación pero conservar `aerich`, edita el script antes de ejecutarlo.
