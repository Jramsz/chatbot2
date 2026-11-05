# Manual de actualización del catálogo

Guía para el personal del MINEDUCYT. No requiere conocimientos de programación.

## Qué se puede editar

Solo el archivo `contenido/intenciones.json`. Contiene todas las preguntas, las
formas de preguntarlas y las respuestas oficiales.

## Estructura de una entrada

```json
{
  "id": "notas-boleta-extravio",
  "categoria": "entrega-notas",
  "subtema": "Boletas",
  "prioridad": 2,
  "pregunta": "¿Qué hago si perdí la boleta de notas?",
  "patrones": [
    "perdí mi boleta de notas",
    "se me extravió el reporte de notas",
    "cómo repongo la boleta",
    "boleta perdida"
  ],
  "respuesta": "Debe solicitar la reposición en la secretaría...",
  "vigencia": "permanente"
}
```

| Campo | Qué poner |
|---|---|
| `id` | Identificador único. **No cambiarlo nunca** una vez publicado. |
| `categoria` | Debe coincidir con una de las categorías declaradas arriba en el archivo. |
| `subtema` | Agrupación dentro de la categoría. |
| `prioridad` | Orden dentro del menú: 1 aparece primero. Use 1 para lo más consultado. |
| `pregunta` | Cómo se muestra la pregunta en el menú. |
| `patrones` | Formas en que un estudiante podría escribir la consulta. Mínimo cuatro, o ninguno (ver más abajo). Entre uno y tres no es válido. |
| `respuesta` | El texto oficial. Debe entenderse por sí solo. |
| `vigencia` | `permanente`, o el año escolar si la respuesta caduca. |
| `activa` | Opcional. Solo se escribe `false` para **retirar** la pregunta (ver más abajo). |

## Cómo escribir buenos patrones

Los patrones son lo que el asistente usa para aprender a reconocer consultas.
Cuanto más variados, mejor funciona.

- **Incluya la forma informal.** Los estudiantes escriben «q hago si perdi mi
  carnet», no «¿cuál es el procedimiento de reposición?».
- **Varíe el vocabulario.** Si la respuesta habla de «boleta», agregue patrones
  con «reporte», «notas» y «calificaciones».
- **No repita la misma frase** en dos intenciones distintas. La validación lo
  detecta y detiene el proceso.
- Los acentos no hace falta duplicarlos: el asistente los ignora.

## Preguntas sin patrones

Una pregunta **sin** patrones (`"patrones": []`) igual aparece en el menú y es
accesible para cualquier estudiante. Lo único que no hace es reconocerse cuando
alguien la escribe libremente. El validador solo muestra un aviso.

Si una pregunta tiene patrones, deben ser **al menos cuatro**; con uno, dos o
tres el validador la rechaza, porque el modelo no alcanzaría a aprenderla.

Esto permite ampliar el catálogo rápido: agregue la pregunta y la respuesta
ahora, y los patrones cuando haya tiempo.

## Después de editar

Envíe el archivo editado al equipo técnico. Hay dos caminos, según lo que
cambió:

| Qué cambió | Qué hace el equipo | Tiempo |
|---|---|---|
| El texto de una pregunta o respuesta, o se agregó una pregunta **sin patrones**, o se movió de categoría | `actualizar_catalogo.py`: valida y regenera solo `catalogo.json`. Se sube ese único archivo. | Segundos |
| Se agregaron o cambiaron **patrones**, o se agregó una pregunta con patrones | `entrenar.py` y la conversión del modelo. Se sube toda la carpeta `web/`. | Minutos |

Mientras no se reentrene, una pregunta nueva con patrones **aparece en el menú**
y se puede consultar por categorías; solo falta que el asistente la reconozca al
escribirla. Si se quita una pregunta que el modelo ya conoce, el menú deja de
mostrarla y, si alguien la escribe, el asistente lo deriva al menú.

La automatización de este flujo está pendiente.

Si el archivo tiene algún error, **no se publica nada** y la versión anterior
sigue funcionando mientras se corrige. Tampoco se publica un modelo que no
alcanza la exactitud mínima o que respondería demasiadas preguntas ajenas al
catálogo.

Cada vez que se agregan o cambian patrones, el equipo técnico revisa además el
resultado de `calibrar.py`, que muestra cuántas preguntas ajenas recibirían
respuesta. Si se agrega al catálogo una pregunta que antes se consideraba ajena
(está en `contenido/fuera-de-alcance.json`), el validador lo avisa y hay que
quitarla de ese archivo.

## Cómo quitar una pregunta

**No borre la entrada.** Agregue `"activa": false` a la pregunta:

```json
{
  "id": "tramites-traslado",
  "activa": false,
  ...
}
```

La pregunta deja de aparecer en el menú y deja de entrenarse, pero su `id`
queda reservado y no puede usarse para otra pregunta. Si borra la entrada, el
sistema lo avisa, porque más adelante alguien podría reutilizar ese `id`.

Si se retira la última pregunta de una categoría, la categoría también deja de
mostrarse. Para volver a mostrar una pregunta, quite la línea `"activa": false`.

Si el modelo ya conocía la pregunta, mientras no se reentrene el asistente, si
alguien la escribe, lo deriva al menú.

## Qué no hacer

- No borrar una pregunta publicada: retírela con `"activa": false`.
- No cambiar el `id` de una entrada existente.
- No borrar las comas ni las llaves de la estructura.
- No escribir una categoría que no exista en la lista de categorías.
- No dejar la respuesta vacía.
