## Validación de pruebas omitidas

Pytest no se considera completamente exitoso si las pruebas de integración fueron omitidas por falta de configuración.

Ejecutá Pytest mostrando los motivos de todas las pruebas omitidas:

```bash
.venv/bin/python -m pytest \
  --cov=app \
  --cov-report=term-missing \
  -rs
```

Después de ejecutarlo, revisá:

* cantidad de pruebas recolectadas;
* cantidad de pruebas aprobadas;
* cantidad de pruebas fallidas;
* cantidad de pruebas omitidas;
* motivo de cada prueba omitida.

Si alguna prueba se omite porque `TEST_DATABASE_URL` no está definida:

1. No declares que las validaciones quedaron al 100%.
2. No inventes una URL de conexión.
3. Buscá la configuración existente mediante:

```bash
rg -n "TEST_DATABASE_URL|DATABASE_URL|POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD" \
  .github docker-compose*.yml .env .env.example tests/conftest.py 2>/dev/null
```

4. Identificá:

    * host;
    * puerto;
    * nombre de la base;
    * usuario;
    * origen seguro de la contraseña;
    * configuración utilizada por GitHub Actions.

5. Verificá que la base esté destinada exclusivamente a pruebas.

6. No ejecutes pruebas contra bases de producción, QA, desarrollo compartido ni bases que contengan información importante.

7. Si no existe una base local exclusiva para pruebas o es necesario crearla, modificar Docker Compose, configurar credenciales o cambiar variables de entorno, detenete y pedime autorización.

La solicitud debe ser similar a:

> Las pruebas de integración fueron omitidas porque `TEST_DATABASE_URL` no está definida. Para ejecutarlas necesito configurar una base PostgreSQL exclusiva para pruebas y definir la variable de entorno correspondiente. ¿Me autorizás a realizar esta configuración?

Después de recibir autorización, configurá `TEST_DATABASE_URL` utilizando los datos reales del proyecto.

Antes de ejecutar las pruebas, verificá que esté disponible:

```bash
.venv/bin/python -c "import os; value = os.getenv('TEST_DATABASE_URL'); print('definida' if value else 'no definida')"
```

No muestres contraseñas ni la URL completa en el informe.

Una vez configurada, ejecutá primero las pruebas de integración:

```bash
.venv/bin/python -m pytest \
  tests/integration \
  -vv -s --tb=long -rs
```

Luego ejecutá la suite completa:

```bash
.venv/bin/python -m pytest \
  --cov=app \
  --cov-report=term-missing \
  -rs
```

Las tres pruebas smoke del LLM pueden permanecer omitidas cuando `RUN_LLM_SMOKE_TESTS` no esté definida, siempre que estén documentadas como pruebas opcionales que requieren un servicio LLM real.

Las pruebas de integración que dependen de `TEST_DATABASE_URL` no deben omitirse en la validación completa del backend.

## Criterio adicional de finalización

Pytest solamente se considera validado al 100% cuando:

* finaliza con código de salida `0`;
* las pruebas unitarias se ejecutan correctamente;
* las pruebas de integración se ejecutan correctamente;
* las pruebas E2E determinísticas se ejecutan correctamente;
* no existen pruebas omitidas por falta de `TEST_DATABASE_URL`;
* cualquier prueba smoke omitida está identificada como opcional;
* el resultado es equivalente al pipeline de GitHub Actions.

Un resultado como el siguiente no debe declararse al 100%:

```text
74 passed, 26 skipped
```

si las pruebas omitidas incluyen pruebas de integración o E2E.

El resultado esperado puede contener las pruebas smoke opcionales omitidas, por ejemplo:

```text
97 passed, 3 skipped
```

siempre que esas tres pruebas correspondan exclusivamente a los smoke tests que requieren `RUN_LLM_SMOKE_TESTS`.
