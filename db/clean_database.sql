-- Borra todos los datos de las tablas del esquema public y reinicia secuencias.
-- Incluye la tabla de control de migraciones (aerich).

BEGIN;

DO $$
DECLARE
  stmt text;
BEGIN
  SELECT
    'TRUNCATE TABLE ' || string_agg(format('%I.%I', schemaname, tablename), ', ')
    || ' RESTART IDENTITY CASCADE'
  INTO stmt
  FROM pg_tables
  WHERE schemaname = 'public';

  IF stmt IS NULL THEN
    RAISE NOTICE 'No public tables found.';
    RETURN;
  END IF;

  EXECUTE stmt;
END $$;

COMMIT;
