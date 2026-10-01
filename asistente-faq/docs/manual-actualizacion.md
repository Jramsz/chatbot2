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
| `prioridad` | Qué tan frecuente es la consulta: 1 es lo más preguntado. Determina qué entra antes al entrenamiento. |
| `pregunta` | Cómo se muestra la pregunta en el menú. |
| `patrones` | Formas en que un estudiante podría escribir la consulta. Mínimo cuatro. |
| `respuesta` | El texto oficial. Debe entenderse por sí solo. |
| `vigencia` | `permanente`, o el año escolar si la respuesta caduca. |

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

Una pregunta **sin** patrones igual aparece en el menú y es accesible para
cualquier estudiante. Lo único que no hace es reconocerse cuando alguien la
escribe libremente.

Esto permite ampliar el catálogo rápido: agregue la pregunta y la respuesta
ahora, y los patrones cuando haya tiempo.

## Después de editar

Al guardar los cambios, el proceso automático valida el archivo, reentrena el
modelo y publica la nueva versión.

Si el archivo tiene algún error, **no se publica nada** y se recibe un aviso. La
versión anterior sigue funcionando mientras se corrige.

## Qué no hacer

- No cambiar el `id` de una entrada existente.
- No borrar las comas ni las llaves de la estructura.
- No escribir una categoría que no exista en la lista de categorías.
- No dejar la respuesta vacía.
