# Asistente de preguntas frecuentes — MINEDUCYT

Asistente conversacional para estudiantes de educación básica y bachillerato.
Clasifica consultas escritas en lenguaje libre mediante una red neuronal
entrenada con TensorFlow, y entrega la respuesta institucional correspondiente.

El modelo se entrena en Python y se ejecuta **en el navegador del estudiante**
con TensorFlow.js. No hay servidor de aplicación: la publicación consiste en
subir archivos estáticos.

> Contexto completo del proyecto, invariantes de diseño y decisiones ya tomadas:
> ver `CLAUDE.md` en la raíz del repositorio.

---

## Estado de la licencia

**Pendiente de definición.** La titularidad de este desarrollo debe confirmarse
con el supervisor empresarial del MINEDUCYT y con el reglamento de propiedad
intelectual de la universidad antes de publicar el repositorio.

El código es original y no deriva de proyectos con licencia copyleft, por lo que
no existe obligación heredada: la licencia se elige libremente una vez resuelta
la titularidad.

---

## Estructura

```
asistente-faq/
├── CLAUDE.md                     Contexto e invariantes del proyecto
├── contenido/
│   └── intenciones.json          Catálogo: preguntas, patrones y respuestas
├── entrenamiento/
│   ├── preprocesamiento.py       Normalización de texto en español
│   ├── validar.py                Validación del catálogo
│   ├── verificar_equivalencia.py Compara Python contra JavaScript
│   └── entrenar.py               Entrenamiento, evaluación y exportación
├── web/
│   ├── index.html
│   ├── estilos.css
│   ├── preprocesamiento.js       Copia gemela de la versión Python
│   ├── motor.js                  Clasificación y navegación
│   ├── interfaz.js               Presentación de la conversación
│   ├── datos/                    Generado: catálogo, vocabulario, clases
│   └── modelo/                   Generado: modelo convertido
└── docs/
    └── manual-actualizacion.md
```

Solo `contenido/intenciones.json` requiere edición para actualizar el
contenido. Las carpetas `web/datos/` y `web/modelo/` se generan.

---

## Puesta en marcha

Todo se instala dentro de entornos virtuales; nada va al sistema.

```bash
# Python (entrenamiento). Requiere Python 3.9 a 3.12.
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Conversion a TensorFlow.js: entorno aparte, porque tensorflowjs arrastra su
# propio subconjunto de TensorFlow y puede chocar con el de arriba.
python -m venv .venv-conversion
.venv-conversion/bin/pip install tensorflowjs==4.22.0

# Librerias del navegador (npm). Copia TensorFlow.js a web/lib/.
npm ci
npm run libs
```

`web/lib/tf.min.js` ya viene incluido en el repositorio; `npm run libs` solo
hace falta al actualizar la version en `package.json`.
```

### 1. Validar el catálogo

```bash
python entrenamiento/validar.py
```

Detecta identificadores duplicados, campos vacíos, categorías inexistentes,
intenciones con patrones insuficientes y patrones que colisionan entre
intenciones distintas.

### 2. Verificar la equivalencia del preprocesamiento

```bash
python entrenamiento/verificar_equivalencia.py
```

**Obligatorio antes de publicar.** Requiere Node.js. Comprueba que las
versiones Python y JavaScript producen los mismos tokens. Si divergen, el
modelo clasifica mal sin emitir ningún error visible.

### 3. Entrenar

```bash
python entrenamiento/entrenar.py
```

Entrena, evalúa sobre un conjunto de prueba reservado y exporta el modelo junto
con el vocabulario, las clases y el catálogo. Si la exactitud queda por debajo
del umbral definido en `EXACTITUD_MINIMA`, el proceso se detiene sin publicar.

### 4. Convertir el modelo para el navegador

```bash
.venv-conversion/bin/tensorflowjs_converter --input_format keras \
    modelo/modelo.h5 web/modelo
```

### 5. Probar en local

```bash
cd web && python -m http.server 8000
```

Abrir `http://localhost:8000`. Un servidor local es necesario: abrir el archivo
directamente impide que el navegador cargue el modelo y los datos.

---

## Decisiones de diseño

**El preprocesamiento no usa NLTK ni ninguna biblioteca de procesamiento de
lenguaje.** Los lematizadores y stemmers de biblioteca no tienen equivalente
exacto en JavaScript, y reimplementarlos introduce divergencia entre
entrenamiento y uso. Las reglas de `preprocesamiento.py` son simples,
deterministas y portables por construcción, y su equivalencia es verificable.

**Una sola respuesta por intención.** El asistente entrega siempre el mismo
texto oficial para la misma consulta. Variar la redacción abriría un problema
de consistencia institucional.

**El menú no depende del modelo.** Si el modelo falla al cargar o no alcanza
confianza suficiente, el asistente sigue siendo plenamente funcional mediante
navegación por categorías. El modelo es una vía de acceso adicional, no un
requisito de funcionamiento.

**Umbral de confianza explícito.** Definido en `motor.js`. Por debajo de él el
asistente no responde: deriva al menú. Para una institución pública, entregar
información incorrecta es más perjudicial que no responder.

**El orden del vocabulario y de las clases es parte del contrato.** Si
`vocabulario.json` o `clases.json` cambian sin reentrenar el modelo, las
predicciones se desalinean silenciosamente. Ambos archivos se generan siempre
junto con el modelo, nunca por separado.

---

## Despliegue

El entregable son archivos estáticos: la carpeta `web/` completa, con `datos/`
y `modelo/` ya generados. Puede publicarse en cualquier servicio de páginas
estáticas o en el servidor web de la institución, y embeberse en el sitio
mediante inserción por URL.

No se usan rutas absolutas: el asistente funciona en cualquier dominio o
subdirectorio sin modificaciones.

---

## Pendientes

- [ ] Definir titularidad y licencia con el supervisor
- [ ] Acordar `EXACTITUD_MINIMA` y `UMBRAL_CONFIANZA` con el supervisor
- [ ] Obtener el catálogo del MINEDUCYT ordenado por frecuencia de consulta
- [ ] Automatizar validación, entrenamiento y conversión en el flujo de publicación
- [ ] Empaquetar TensorFlow.js localmente para producción
- [ ] Prueba con estudiantes reales y ampliación de patrones según resultados
