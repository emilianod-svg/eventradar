---

description: Ejecuta y corrige todas las validaciones de calidad del backend hasta dejarlas al 100%
agent: build
------------

Tu objetivo es conseguir que todas las validaciones de calidad del backend finalicen correctamente.

## Autorización obligatoria

Antes de ejecutar comandos o modificar archivos:

1. Informá que vas a ejecutar las cuatro validaciones.
2. Indicá que, si aparecen errores, modificarás el código para corregirlos.
3. Pedí mi autorización explícita para comenzar.
4. Esperá mi respuesta.

No ejecutes comandos ni modifiques archivos hasta que responda afirmativamente.

Una vez autorizado, podés ejecutar los comandos, analizar errores, modificar el código y repetir las validaciones sin solicitar autorización en cada corrección.

## Validaciones

Ejecutá desde la raíz del proyecto, en este orden:

1. `ruff check .`
2. `ruff format --check .`
3. `mypy app`
4. `pytest`

## Proceso de corrección

Después de recibir mi autorización:

1. Ejecutá las validaciones.
2. Si una validación falla:

    * identificá el comando que falló;
    * analizá el archivo, la línea y la causa;
    * corregí el código;
    * ejecutá nuevamente la validación afectada.
3. Continuá con la siguiente validación cuando la anterior finalice correctamente.
4. Repetí el proceso de análisis, corrección y validación hasta que todos los comandos pasen.
5. Después de realizar correcciones, ejecutá nuevamente las cuatro validaciones completas para detectar regresiones.

## Reglas

* Podés modificar archivos del proyecto después de recibir mi autorización.
* Podés usar `ruff check --fix .` únicamente para correcciones seguras y automáticas.
* Podés usar `ruff format .` cuando falle `ruff format --check .`.
* Revisá los cambios generados automáticamente antes de continuar.
* No elimines pruebas ni reduzcas su cobertura para conseguir que `pytest` pase.
* No agregues `# noqa`, `# type: ignore`, exclusiones de Ruff o configuraciones de MyPy solamente para ocultar errores.
* No debilites las validaciones existentes.
* No cambies dependencias, versiones, migraciones, variables de entorno ni configuraciones sensibles sin solicitar una nueva autorización.
* No realices `commit`, `push`, `merge` ni operaciones destructivas.
* Conservá el comportamiento funcional existente, salvo que una corrección legítima requiera modificarlo.
* Si existen varias soluciones posibles con consecuencias funcionales diferentes, explicalas y pedime que elija antes de modificar el código.
* Si un error depende de un servicio externo, credenciales, infraestructura o información que no tenés, detenete y explicá el bloqueo.

## Criterio de finalización

La tarea solamente está terminada cuando estos cuatro comandos finalizan con código de salida `0`:

```bash
ruff check .
ruff format --check .
mypy app
pytest
```

Al finalizar, informá:

* qué errores encontraste;
* qué archivos modificaste;
* qué correcciones realizaste;
* el resultado final de cada comando;
* si las cuatro validaciones quedaron al 100%.

No declares que la tarea terminó correctamente si alguna validación continúa fallando.
