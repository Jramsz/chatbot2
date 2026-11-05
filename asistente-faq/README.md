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
.venv-conversion/bin/pip install tensorflowjs==4.22.0 ydf==0.13.0

# Librerias del navegador (pnpm). Copia TensorFlow.js a web/lib/.
pnpm install --frozen-lockfile
pnpm run libs
```

`web/lib/tf.min.js` ya viene incluido en el repositorio; `pnpm run libs` solo
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

Mide el modelo con validación cruzada de 5 pliegues y solo publica si cumple
**las dos** condiciones (provisionales, a revisar con el contenido real):

- `EXACTITUD_MINIMA` (0.75): aciertos sobre los patrones del catálogo.
- `AJENAS_MAXIMA` (15 %): consultas de `fuera-de-alcance.json` que recibirían
  respuesta con el umbral y la cobertura de `web/motor.js`.

Si cumple, reentrena con todos los patrones y exporta el modelo junto con el
vocabulario, las clases y el catálogo. Si no, se detiene sin publicar e indica
por qué. También muestra las intenciones que más se confunden entre sí, que es
donde conviene reforzar patrones. Tarda unos minutos.

Las intenciones sin patrones no se entrenan: solo aparecen en el menú.

### 4. Convertir el modelo para el navegador

```bash
.venv-conversion/bin/tensorflowjs_converter --input_format keras \
    modelo/modelo.h5 web/modelo
```

Notas de la conversión (verificadas con TensorFlow.js 4.22.0):

- El modelo se guarda en formato Keras 2 (`tf-keras`, ya incluido en
  `requirements.txt`). El `.h5` de Keras 3 no sirve: TensorFlow.js falla al
  cargarlo (capa de entrada y nombres de pesos distintos).
- `ydf` se fija en 0.13.0 porque versiones más nuevas chocan con el protobuf de
  `tensorflowjs` y el conversor ni siquiera arranca.

### 5. Probar en local

```bash
cd web && python -m http.server 8000
```

Abrir `http://localhost:8000`. Un servidor local es necesario: abrir el archivo
directamente impide que el navegador cargue el modelo y los datos.

### Actualización rápida: solo cambió un texto o se agregó una pregunta al menú

```bash
python entrenamiento/actualizar_catalogo.py --revisar   # muestra los cambios
python entrenamiento/actualizar_catalogo.py             # valida y regenera catalogo.json
```

Actualiza únicamente `web/datos/catalogo.json`, sin TensorFlow y sin reentrenar.
Publicar solo ese archivo. Si hay que agregar o cambiar patrones, usar el flujo
completo (pasos 3 y 4).

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

**No responder por aproximación.** El asistente solo responde si la confianza
supera `UMBRAL_CONFIANZA`, si conoce al menos `COBERTURA_MINIMA` de los términos
de la consulta y si el modelo no la clasifica como «fuera de alcance» (una clase
entrenada con `contenido/fuera-de-alcance.json`). En cualquier otro caso deriva
al menú. Los valores se calibran con `entrenamiento/calibrar.py`.

**El orden del vocabulario y de las clases es parte del contrato.** Si
`vocabulario.json` o `clases.json` cambian sin reentrenar el modelo, las
predicciones se desalinean silenciosamente. Ambos archivos se generan siempre
junto con el modelo, nunca por separado.

---

## Despliegue

Un solo comando arma el entregable: valida, verifica la equivalencia, entrena
(con sus condiciones), convierte el modelo y comprueba que modelo, vocabulario y
clases coinciden.

```bash
python entrenamiento/publicar.py                 # todo
python entrenamiento/publicar.py --sin-entrenar  # reusa el modelo ya generado
```

Resultado en `entrega/`: `asistente/` es el widget que se entrega (archivos
estáticos) e `index.html` es una página de demostración con el widget
embebido. Para insertarlo en un sitio basta una línea (ver
`docs/integracion.md`):

```html
<script src="https://<donde-este-alojado>/asistente/insertar.js" defer></script>
```

**Publicación automática.** Cada cambio en `asistente-faq/` que llega a `main`
ejecuta `.github/workflows/publicar.yml`: pruebas, `publicar.py` y despliegue
en GitHub Pages. Si algo falla, no se publica y sigue la versión anterior.
Requisito: en GitHub, Settings > Pages > Source = «GitHub Actions».

No se usan rutas absolutas: el asistente funciona en cualquier dominio o
subdirectorio sin modificaciones.

---

## Pendientes

- [ ] Definir titularidad y licencia con el supervisor
- [ ] Acordar `EXACTITUD_MINIMA`, `AJENAS_MAXIMA`, `UMBRAL_CONFIANZA` y
      `COBERTURA_MINIMA` con el supervisor (ver la tabla de
      `python entrenamiento/calibrar.py`) y volver a medirlos con el contenido real
- [ ] Obtener el catálogo del MINEDUCYT ordenado por frecuencia de consulta
- [x] Automatizar validación, entrenamiento y conversión (`publicar.py` y GitHub Actions)
- [ ] Prueba con estudiantes reales y ampliación de patrones según resultados
