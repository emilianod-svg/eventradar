---

description: Ejecuta las validaciones de calidad del backend y solicita autorización antes de corregir errores
agent: build
------------

Tu objetivo es verificar que todas las validaciones de calidad del backend finalicen correctamente y, si encontrás errores, corregirlos únicamente después de recibir mi autorización.

## Inicio de la validación

Podés ejecutar comandos de diagnóstico y las cuatro validaciones iniciales sin solicitar autorización.

Antes de comenzar:

1. Informá que vas a ejecutar las cuatro validaciones.
2. No modifiques archivos ni apliques correcciones automáticas durante esta primera ejecución.
3. Verificá que estás ubicado en la raíz real del backend.
4. Usá obligatoriamente el entorno virtual `.venv` del backend.
5. Ejecutá todas las validaciones dentro del mismo entorno y contexto de consola.

## Verificación obligatoria del entorno

Antes de ejecutar las validaciones, comprobá y mostr á:

```bash
pwd
test -d app
test -f pyproject.toml
test -x .venv/bin/python
.venv/bin/python --version
.venv/bin/python -c "import sys; print(sys.executable)"
.venv/bin/python -m mypy --version
.venv/bin/python -m pytest --version
.venv/bin/python -m ruff --version
```

La ruta mostrada por `sys.executable` debe corresponder al archivo:

```text
<raíz-del-backend>/.venv/bin/python
```

Si `.venv` no existe, no contiene las herramientas necesarias o no corresponde al backend actual, detenete y explicá el problema. No instales ni actualices dependencias sin mi autorización.

No uses el Python, Ruff, MyPy o Pytest instalados globalmente en el sistema.

## Validaciones iniciales

Ejecutá desde la raíz del backend y en este orden:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy app
.venv/bin/python -m pytest
```

No reemplaces estos comandos por validaciones parciales.

No omitas archivos, módulos, directorios o pruebas para conseguir un resultado exitoso.

Registrá para cada comando:

* comando exacto ejecutado;
* directorio de ejecución;
* salida relevante;
* código de salida;
* cantidad de archivos analizados, cuando la herramienta lo informe.

Una validación solamente se considera correcta si el comando correspondiente finaliza con código de salida `0`.

## Autorización para corregir errores

Si las cuatro validaciones finalizan correctamente, informá el resultado y terminá la tarea sin solicitar autorización.

Si alguna validación falla:

1. Detenete en la primera validación que falle.

2. No modifiques ningún archivo todavía.

3. No ejecutes `ruff check --fix .` ni `ruff format .`.

4. Informá:

    * el comando exacto que falló;
    * el código de salida;
    * el archivo y la línea;
    * el mensaje completo del error;
    * la causa probable;
    * la corrección recomendada;
    * los archivos que sería necesario modificar.

5. Pedí mi autorización explícita para aplicar las correcciones.

6. Esperá mi respuesta antes de modificar archivos.

La pregunta debe ser clara, por ejemplo:

> Encontré errores en `mypy app`. Para corregirlos necesito modificar `app/agents/evaluator.py`. ¿Me autorizás a realizar las correcciones y repetir todas las validaciones hasta dejarlas al 100%?

No interpretes una respuesta ambigua como autorización.

## Proceso posterior a la autorización

Después de recibir mi autorización:

1. Corregí el error detectado.
2. Ejecutá nuevamente la validación afectada.
3. Si aparecen nuevos errores de la misma naturaleza y la solución no cambia el comportamiento funcional, podés continuar corrigiéndolos sin solicitar autorización nuevamente.
4. Cuando la validación pase, continuá con la siguiente.
5. Repetí el proceso hasta que las cuatro validaciones pasen.
6. Al terminar las correcciones, ejecutá nuevamente la suite completa:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy app
.venv/bin/python -m pytest
```

## Reglas para las correcciones

* Revisá cada cambio antes de continuar.
* Podés usar `.venv/bin/python -m ruff check --fix .` solamente después de mi autorización y para correcciones seguras.
* Podés usar `.venv/bin/python -m ruff format .` solamente después de mi autorización.
* No elimines, deshabilites ni alteres pruebas para conseguir que Pytest pase.
* No reduzcas la cobertura.
* No agregues `# noqa`, `# type: ignore`, exclusiones de Ruff o configuraciones de MyPy solamente para ocultar errores.
* No debilites las validaciones existentes.
* No cambies dependencias, versiones, migraciones, variables de entorno ni configuraciones sensibles sin solicitar una nueva autorización.
* No realices `commit`, `push`, `merge`, `rebase`, `reset` ni operaciones destructivas.
* Conservá el comportamiento funcional existente.
* Si existen varias soluciones con consecuencias funcionales diferentes, explicalas y pedime que elija antes de modificar el código.
* Si un error depende de servicios externos, credenciales, infraestructura o información no disponible, detenete y explicá el bloqueo.
* No declares un comando como exitoso basándote en una ejecución anterior.
* No uses resultados almacenados en otra terminal, otro entorno virtual, otro contenedor o una ejecución previa.
* No confundas un problema del entorno con un error del código.
* No declares `mypy app` como correcto si la salida contiene errores, aunque otro comando de MyPy haya finalizado correctamente.

## Caso conocido que debe verificarse

Prestá especial atención a `app/agents/evaluator.py`.

Una ejecución real de:

```bash
mypy app
```

dentro del `.venv` reportó errores como:

```text
Argument 1 to "_candidate_payload" of "EvaluatorAgent" has incompatible type
"Mapping[str, Any] | EventCandidate | Event";
expected "Mapping[str, Any] | EventCandidate" [arg-type]
```

Los errores fueron detectados aproximadamente en las líneas:

```text
417
511
522
536
```

No asumas que estos errores ya están corregidos. Verificá el contenido actual del archivo y ejecutá MyPy usando explícitamente:

```bash
.venv/bin/python -m mypy app
```

Si estos errores aparecen, detenete, explicá la incompatibilidad de tipos y pedime autorización antes de modificar `app/agents/evaluator.py`.

## Criterio de finalización

La tarea solamente está terminada cuando los siguientes cuatro comandos, ejecutados desde la raíz actual del backend y utilizando su `.venv`, finalizan con código de salida `0`:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy app
.venv/bin/python -m pytest
```

## Informe final

Al finalizar, informá:

* entorno virtual utilizado;
* ruta del intérprete;
* errores encontrados;
* archivos modificados;
* correcciones realizadas;
* comando exacto y código de salida de cada validación;
* resultado final de Ruff Check;
* resultado final de Ruff Format;
* resultado final de MyPy;
* resultado final de Pytest;
* confirmación de si las cuatro validaciones quedaron al 100%.

No declares que la tarea terminó correctamente si alguna validación continúa fallando o si fue ejecutada fuera del `.venv` correspondiente al backend.
