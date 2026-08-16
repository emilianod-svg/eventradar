---

description: Ejecuta las validaciones de calidad del backend y solicita autorización antes de corregir errores
agent: build
------------

Tu objetivo es verificar y corregir todas las validaciones de calidad del backend hasta dejarlas al 100%.

## Ejecución inicial

Podés ejecutar las validaciones iniciales sin solicitar autorización.

Antes de comenzar:

1. Informá que vas a ejecutar las cuatro validaciones.
2. Ubicate en la raíz del backend.
3. Verificá que exista el entorno virtual `.venv`.
4. No modifiques archivos ni apliques correcciones automáticas durante esta primera ejecución.

## Entorno virtual obligatorio

Todas las validaciones deben ejecutarse usando explícitamente el Python del entorno virtual del backend.

Primero verificá:

```bash
pwd
test -d app
test -f pyproject.toml
test -x .venv/bin/python
.venv/bin/python -c "import sys; print(sys.executable)"
.venv/bin/python -m ruff --version
.venv/bin/python -m mypy --version
.venv/bin/python -m pytest --version
```

La ruta informada por `sys.executable` debe terminar en:

```text
backend/.venv/bin/python
```

No ejecutes directamente:

```bash
ruff
mypy
pytest
```

Esos comandos podrían utilizar instalaciones globales de Ubuntu y producir resultados diferentes.

Usá siempre `.venv/bin/python -m ...`.

Si `.venv` no existe o alguna herramienta no está instalada dentro del entorno virtual, detenete y explicá el problema. No instales ni actualices dependencias sin mi autorización.

## Validaciones

Ejecutá desde la raíz del backend, en este orden:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy app
.venv/bin/python -m pytest
```

Para cada validación registrá:

* comando exacto;
* directorio de ejecución;
* salida relevante;
* código de salida.

Una validación solamente se considera correcta si finaliza con código de salida `0`.

## Cuando una validación falla

Detenete en la primera validación que falle.

Antes de modificar archivos:

1. Identificá el comando que falló.
2. Informá el código de salida.
3. Indicá el archivo y la línea del error.
4. Mostrá el mensaje relevante.
5. Explicá la causa probable.
6. Indicá la corrección recomendada.
7. Enumerá los archivos que necesitarías modificar.
8. Pedí mi autorización explícita para aplicar las correcciones.
9. Esperá mi respuesta.

La solicitud debe ser similar a:

> Encontré errores al ejecutar `.venv/bin/python -m mypy app`. Para corregirlos necesito modificar `app/agents/evaluator.py`. ¿Me autorizás a aplicar las correcciones y repetir las validaciones hasta dejarlas al 100%?

No modifiques archivos ni ejecutes comandos de corrección automática hasta recibir una respuesta afirmativa.

## Después de recibir autorización

Una vez autorizado:

1. Aplicá la corrección.
2. Revisá los cambios realizados.
3. Ejecutá nuevamente la validación afectada.
4. Continuá con la siguiente validación solamente cuando la anterior pase.
5. Repetí el proceso hasta que las cuatro validaciones finalicen correctamente.
6. No solicites autorización por cada corrección del mismo tipo.
7. Si aparece una decisión con consecuencias funcionales diferentes, detenete, explicá las alternativas y pedime que elija.

## Validación final completa

Después de realizar correcciones, ejecutá nuevamente las cuatro validaciones completas:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy app
.venv/bin/python -m pytest
```

Esto es obligatorio aunque cada validación haya pasado individualmente durante el proceso.

## Reglas

* Podés modificar archivos únicamente después de recibir mi autorización.
* Podés usar `.venv/bin/python -m ruff check --fix .` solamente después de mi autorización y para correcciones seguras.
* Podés usar `.venv/bin/python -m ruff format .` solamente después de mi autorización.
* Revisá todos los cambios automáticos.
* No elimines, deshabilites ni modifiques pruebas para conseguir que Pytest pase.
* No reduzcas la cobertura.
* No agregues `# noqa` o `# type: ignore` solamente para ocultar errores.
* No agregues exclusiones de Ruff o MyPy para ocultar problemas.
* No debilites las validaciones existentes.
* No cambies dependencias, versiones, migraciones, variables de entorno ni configuraciones sensibles sin solicitar una nueva autorización.
* No realices `commit`, `push`, `merge`, `rebase`, `reset` ni operaciones destructivas.
* Conservá el comportamiento funcional existente.
* No uses resultados de ejecuciones anteriores.
* No uses otro entorno virtual.
* No uses el Python global del sistema.
* No declares una validación como correcta si no fue ejecutada con `.venv/bin/python`.
* Si un error depende de servicios externos, credenciales o infraestructura, detenete y explicá el bloqueo.

## Criterio de finalización

La tarea solamente estará terminada cuando estos cuatro comandos finalicen con código de salida `0`:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy app
.venv/bin/python -m pytest
```

## Informe final

Al finalizar, informá:

* raíz del backend utilizada;
* ruta del intérprete de Python;
* entorno virtual utilizado;
* errores encontrados;
* archivos modificados;
* correcciones realizadas;
* comando exacto ejecutado para cada validación;
* código de salida de cada comando;
* resultado final de Ruff Check;
* resultado final de Ruff Format;
* resultado final de MyPy;
* resultado final de Pytest;
* confirmación de si las cuatro validaciones quedaron al 100%.

No declares que la tarea terminó correctamente si alguna validación continúa fallando o fue ejecutada fuera del `.venv` del backend.
