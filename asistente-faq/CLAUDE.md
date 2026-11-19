# Contexto del proyecto

Asistente conversacional de preguntas frecuentes para el **MINEDUCYT**
(Ministerio de Educación, Ciencia y Tecnología de El Salvador).

Proyecto de práctica profesional, Universidad Gerardo Barrios.
Equipo: Darien Molina (dirección y diseño), José Arias (datos y modelo),
Oscar Álvarez (widget, exportación y calidad).
Entrega: diciembre de 2026.

---

## Qué es

Clasificador de intenciones en español entrenado con TensorFlow/Keras, que
responde consultas de estudiantes de educación básica y bachillerato sobre
trámites, notas y útiles escolares.

Se entrega como **widget embebible**. El modelo se convierte a TensorFlow.js
y **se ejecuta en el navegador del estudiante**. El entrenamiento ocurre en
Python, fuera de línea.

**El despliegue en producción lo hace el ministerio, no el equipo.** El
entregable es una carpeta de archivos estáticos.

---

## Invariantes

Estas reglas sostienen el proyecto. No cambiarlas sin decisión explícita del
equipo; romper cualquiera invalida la propuesta aprobada.

### 1. No existe servidor de inferencia

Toda la clasificación ocurre en el dispositivo del usuario. No agregar
servicios que procesen consultas, ni llamadas de red durante el uso.

**Razón:** es lo que permite atender ~300,000 consultas mensuales con costo
operativo cero. La alternativa (modelo en servidor) costaría varios miles de
dólares al mes y fue descartada por eso.

Formulación correcta cuando haya que explicarlo:

> El servidor entrega el catálogo y el modelo una vez. La clasificación y la
> navegación ocurren en el dispositivo del estudiante, sin volver a consultar
> al servidor.

El editor del catálogo (`editor/`) tampoco es un servidor: es una página
estática que, solo para administradores, guarda en el repositorio mediante la
API de GitHub. El control de acceso lo hace GitHub (token con permiso de
escritura); no agregar contraseñas propias en el cliente, no protegerían nada.

Nunca decir «no hay servidor»: sí hay un servicio que entrega archivos
estáticos. Lo que no hay es lógica de servidor.

### 2. El preprocesamiento debe ser idéntico en Python y JavaScript

`entrenamiento/preprocesamiento.py` y `web/preprocesamiento.js` son copias
gemelas. Cualquier cambio en uno debe replicarse en el otro.

```bash
python entrenamiento/verificar_equivalencia.py
```

**Obligatorio antes de publicar.** Si divergen, el modelo clasifica mal sin
emitir ningún error: es un fallo silencioso, y el riesgo más crítico del
proyecto.

No introducir NLTK, spaCy ni ningún lematizador de biblioteca. No tienen
equivalente exacto en JavaScript. Las reglas actuales son deliberadamente
simples y portables.

Si se migra a una capa de incrustación con secuencia de longitud fija, el
contrato se amplía: además del vocabulario y su orden, incluye relleno y
truncado. La verificación debe cubrirlos.

### 3. Una sola respuesta por intención

El campo `respuesta` es un texto único, nunca una lista. Los repositorios de
referencia eligen al azar entre varias; para una institución pública eso es
inaceptable: dos estudiantes con la misma consulta deben recibir el mismo
texto oficial.

### 4. El menú funciona sin el modelo

`motor.js` carga el catálogo primero y el modelo después, en segundo plano. Si
el modelo falla al cargar, el asistente sigue operando por navegación de
categorías.

El menú cubre **el 100 % del catálogo**; el modelo solo el subconjunto
entrenado. No introducir rutas donde el usuario quede sin salida si el modelo
no responde.

### 5. Umbral de confianza: no responder por aproximación

Tres defensas, todas en el camino de la consulta escrita:

- `UMBRAL_CONFIANZA` (`motor.js`): probabilidad mínima de la intención elegida.
- `COBERTURA_MINIMA` (`motor.js`): fracción mínima de los términos de la
  consulta que el modelo conoce. Con bolsa de palabras, una consulta ajena que
  comparte una sola palabra con el catálogo puede recibir confianza alta.
- Clase `fuera-de-alcance`: el modelo se entrena también con
  `contenido/fuera-de-alcance.json`. Esa clase no está en el catálogo, así que
  el navegador deriva al menú (id reservado).

Por debajo de cualquiera se deriva al menú, nunca se entrega la intención más
probable. Los valores se eligen con `entrenamiento/calibrar.py`, que mide cuántas
consultas ajenas reciben respuesta; no cambiarlos sin volver a medir.
`entrenar.py` lee esos valores de `motor.js` (una sola fuente) y no publica si
las consultas ajenas respondidas superan `AJENAS_MAXIMA`, ni si el modelo final
responde con una intención equivocada alguna consulta de
`contenido/consultas-de-aceptacion.json`. Cada respuesta equivocada que alguien
encuentre en el sitio se agrega ahí como caso: así no vuelve a publicarse. El validador impide
que una consulta de `fuera-de-alcance.json` coincida con un patrón del catálogo.

Para una institución pública, informar mal es peor que no responder.

### 6. El orden del vocabulario y las clases es parte del contrato

`vocabulario.json` y `clases.json` se generan **siempre junto con el modelo**,
nunca por separado. Si cambian sin reentrenar, las predicciones se desalinean
en silencio.

Se garantiza por construcción: `entrenar.py` los deja en `modelo/` junto al
`.h5`, y solo `publicar.py` (`instalar_modelo`) los copia a `web/datos/` con el
modelo convertido, después de una conversión exitosa. Si la conversión falla,
`web/` queda intacto. `comprobar_contrato` revisa además las dimensiones, y
`motor.js` las vuelve a revisar al cargar.

### 7. El entregable es portable

Sin rutas absolutas ni dominios fijos. El ministerio elige dónde alojarlo y
debe funcionar sin editar nada.

Esto incluye las dependencias: TensorFlow.js se sirve desde `web/lib/tf.min.js`
(versión 4.22.0, Apache 2.0), nunca desde un CDN. La versión se fija en
`package.json` y se copia con `pnpm run libs`. Una caída del CDN o una
política de red del ministerio dejaría el widget sin modelo y sin aviso.

---

## Alcance: cobertura, no conteo

El catálogo ronda las 500 preguntas, **sin cifra exacta**. El compromiso no es
un número de intenciones sino la cobertura:

- **Catálogo (menú):** cubre todas las preguntas que aporte el ministerio.
  Agregar una cuesta solo redactar la respuesta.
- **Modelo (escritura libre):** cubre el subconjunto priorizado por frecuencia.
  Cada intención requiere además 10 a 20 formulaciones de ejemplo.

Entrenamiento por olas. La ola 1 entrena las intenciones más frecuentes y
produce la primera medición real; el alcance de la ola 2 se acuerda con el
supervisor **después** de esa medición.

**Las métricas objetivo no están fijadas a propósito.** La exactitud alcanzable
depende del número de clases, que aún no se conoce. No comprometer porcentajes
antes de la línea base.

---

## Comandos

Requiere Python 3.9 a 3.12 (límite de TensorFlow 2.17) y Node para la
verificación de equivalencia.

```bash
python -m venv .venv && source .venv/bin/activate   # entrenamiento
pip install -r requirements.txt
python -m venv .venv-conversion                     # solo conversión
.venv-conversion/bin/pip install tensorflowjs==4.22.0 ydf==0.13.0   # ydf fijado: ver nota
pnpm install --frozen-lockfile && pnpm run libs         # librerías del navegador

python entrenamiento/validar.py                 # valida el catálogo
python entrenamiento/verificar_equivalencia.py  # Python contra JS (requiere Node)
python entrenamiento/entrenar.py                # entrena, evalúa y exporta
python entrenamiento/actualizar_catalogo.py    # solo catálogo, sin reentrenar
python entrenamiento/calibrar.py                # mide umbral y cobertura
pnpm test                                       # pruebas del motor (solo Node)
python entrenamiento/publicar.py                # todo lo anterior + conversión → entrega/
python -m unittest discover -s pruebas -p "test_*.py"   # pruebas de Python

# tensorflowjs va en su propio entorno (.venv-conversion) por el conflicto con
# el TensorFlow de requirements.txt.
.venv-conversion/bin/tensorflowjs_converter --input_format keras \
    modelo/modelo.h5 web/modelo

cd web && python -m http.server 8000            # prueba local
```

Abrir el archivo directamente no funciona: hace falta un servidor local para
que el navegador cargue el modelo y los datos.

---

## Estructura

```
contenido/intenciones.json      Catálogo. Único archivo que edita el ministerio.
contenido/fuera-de-alcance.json Consultas que NO deben responderse (lo mantiene el equipo).
contenido/consultas-de-aceptacion.json  Consultas con respuesta esperada; bloquean la publicación.
entrenamiento/                  Python: preprocesamiento, validación, entrenamiento.
web/                            Widget: interfaz, motor, preprocesamiento gemelo.
web/lib/                        TensorFlow.js local, copiado desde pnpm (pnpm run libs).
package.json  scripts/          Versión fijada de las librerías del navegador.
web/datos/  web/modelo/         Generados. No editar a mano.
                                datos/ = vocabulario.json, clases.json, catalogo.json
                                (vocabulario y clases solo los instala publicar.py)
modelo/                         Salida de entrenar.py: modelo.h5, vocabulario.json,
                                clases.json y tfjs/ (convertido). Fuera de git.
docs/manual-actualizacion.md    Guía de contenido para el ministerio.
docs/integracion.md             Guía para insertar el widget en un sitio.
docs/editor.md                  Guía del editor del catálogo para administradores.
editor/                         Editor del catálogo: formularios, valida y guarda en GitHub.
                                validacion.js es gemela de validar.py (ver pruebas).
demo/index.html                 Sitio de ejemplo con el widget embebido (no es entregable).
web/insertar.js                 Botón flotante + marco: lo que pega el sitio anfitrión.
entrega/                        Generado por publicar.py. No editar.
README.md                       Presentación y pasos de uso.
```

---

## Convenciones

- Código, comentarios y documentación en español.
- Los comentarios explican **por qué**, no qué hace la línea.
- Todo texto visible para el usuario vive en `TEXTOS` (`interfaz.js`) o en
  `contenido/`, nunca disperso en el código.
- Accesibilidad: el foco nunca debe quedar perdido en la página (tras
  deshabilitar un botón se mueve a la primera opción nueva), y lo que dice el
  asistente se anuncia por `#anuncio`, no por la conversación completa.
- JavaScript sin framework. El widget debe cargar rápido en conexiones móviles
  lentas y seguir funcionando durante años sin mantenimiento de dependencias.
- El `id` de una intención es permanente. No se reutiliza ni se modifica una
  vez publicado. Para quitar una pregunta no se borra: se marca
  `"activa": false` (sale del menú y del entrenamiento, el id queda reservado).

---

## Decisiones ya tomadas (no reabrir sin motivo)

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| Modelo en el navegador | Modelo en servidor (Flask/Python) | Costo operativo y saturación |
| Código propio | Derivar de los repos de referencia | Licencia GPL-3.0 y dependencias obsoletas |
| TensorFlow/Keras | TFLearn | Sin mantenimiento activo |
| Preprocesamiento propio | NLTK | Sin equivalente exacto en JavaScript |
| Widget embebible | Página en el portal institucional | Desacopla el entregable de la plataforma |
| WhatsApp descartado como canal | WhatsApp Cloud API | ~US$81,000 anuales desde octubre de 2026 |

---

## Pendientes

- [ ] **Listado de preguntas ordenado por frecuencia de consulta** (insumo
      crítico; sin la priorización no puede definirse el alcance de las olas)
- [ ] Titularidad y licencia: confirmar con el supervisor y con el reglamento
      de propiedad intelectual de la universidad. Hasta entonces, repositorio
      sin licencia pública
- [ ] Acordar con el supervisor, mostrando la tabla de `calibrar.py`:
      `EXACTITUD_MINIMA` (0.75, provisional), `AJENAS_MAXIMA` (15 %),
      `UMBRAL_CONFIANZA` (0.9) y `COBERTURA_MINIMA` (0.6). Volver a medir con
      el contenido real: la exactitud depende del número de intenciones
- [x] Automatizar validación, verificación, entrenamiento y conversión:
      `publicar.py` y `.github/workflows/publicar.yml` (GitHub Pages)
- [ ] Si se actualiza `web/lib/tf.min.js`, reconvertir y probar el modelo con
      esa misma versión de TensorFlow.js
- [ ] Designar responsable del contenido y del reentrenamiento en el ministerio
- [ ] Prueba con estudiantes reales y ampliación de patrones según resultados
