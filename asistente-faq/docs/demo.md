# Guion de la demostración

Duración: unos 15 minutos más preguntas. Sitio:
`https://jramsz.github.io/chatbot2/` · Editor: `https://jramsz.github.io/chatbot2/editor/`

Las consultas escritas de este guion están en
`contenido/consultas-de-aceptacion.json`: cada publicación comprueba que el
modelo publicado no responde ninguna con una pregunta equivocada (puede, como
mucho, ofrecer el menú). El registro de la última publicación en *Actions* dice
cuántas respondió bien; revisarlo el día anterior.

## Antes de la demo (el día anterior)

- [ ] En *Actions → Publicar asistente*, la última ejecución está en verde y su
      registro dice «Pruebas de aceptacion: 53/53 correctas» (o indica cuáles
      van al menú: no usar esas en vivo).
- [ ] El sitio abre en una computadora y en un teléfono (recargar con Ctrl+F5).
- [ ] El token del editor está creado (ver `editor.md`), probado y a mano en un
      gestor de contraseñas, no en un documento.
- [ ] Ensayo completo con cronómetro, en la misma red que se usará.
- [ ] Plan B listo (ver al final).

## Guion

### 1. El problema y la idea (1 min)

- Cientos de miles de consultas repetidas al mes sobre notas, trámites y útiles.
- El asistente las responde **en el navegador del estudiante**: el servidor
  solo entrega archivos una vez. Por eso el costo de operación es cero, sin
  importar cuántas consultas haya.

### 2. El sitio de ejemplo y el widget embebido (2 min)

- Abrir el sitio. Señalar que es un sitio cualquiera y que el asistente se
  agrega con **una sola línea** (está escrita en la misma página).
- Pulsar el botón **«¿Tienes dudas? Pregunta aquí»**.
- *Se espera:* saludo y las cuatro categorías.

### 3. Navegar sin escribir (1 min)

- **Notas → ¿Qué hago si perdí la boleta de notas?**
- *Se espera:* la respuesta en dos toques; «← Volver» regresa a las
  categorías.
- Mensaje: el menú cubre el 100 % del catálogo y funciona aunque el modelo no
  cargue.

### 4. Escribir libremente (3 min)

| Escribir | Se espera |
|---|---|
| `como saber mis notas` | ¿Cuándo y cómo puedo ver mis notas? |
| `perdí la boleta de mi hija` | La reposición de la boleta |
| `quiero cambiar a mi hijo a otra escuela` | El traslado |
| `cómo denuncio bullying` | Qué hacer ante acoso o maltrato |
| `quien gano el mundial` | **No responde**: ofrece el menú |

- Mensaje clave en la última: **para una institución pública, informar mal es
  peor que no responder**. Ante la duda, el asistente ofrece el menú.

### 5. En el teléfono (1 min)

- Abrir el sitio en un teléfono: el asistente ocupa la pantalla y el botón ✕
  cierra.
- El menú aparece en ~1.5 s incluso en 3G; el modelo termina de cargar en
  segundo plano.

### 6. El editor para administradores (4 min)

- Abrir el editor e ingresar con el token. Explicar: **solo entran cuentas con
  permiso de escritura en el repositorio; lo controla GitHub**.
- Buscar «carné», abrir la pregunta, cambiar una frase de la respuesta,
  **Aplicar** y **Guardar y publicar**.
- *Se espera:* «Guardado…» y el estado de la publicación («Publicando…»).
- Mientras publica (unos 5 minutos), seguir con el punto 7 y al final mostrar
  la respuesta cambiada en el sitio.
- Mostrar también **Agregar pregunta** con menos de 4 patrones: el editor no
  la acepta y explica por qué.

### 7. Cómo se cuida la calidad (2 min)

Cada publicación, automática, valida el catálogo, verifica que Python y el
navegador procesen igual todos los textos del contenido, entrena, mide y **no publica**
si:

- la exactitud baja de 0.75, o
- respondería más del 15 % de preguntas ajenas, o
- alguna consulta de aceptación recibe una respuesta equivocada.

Si algo falla, el sitio sigue con la versión anterior.

### 8. Límites y decisiones pendientes (2 min)

- **El contenido es de muestra.** El ministerio carga el real con el editor;
  entonces hay que volver a medir.
- **El modelo se equivoca en ~9 % de las frases nuevas** del catálogo de
  muestra; las tres defensas y las pruebas de aceptación evitan que eso llegue a
  las consultas conocidas, y cada error encontrado se agrega como caso.
- **Para el supervisor:** aprobar los umbrales (exactitud 0.75, ajenas 15 %,
  confianza 0.9, cobertura 0.6), la titularidad y la licencia, y quién
  administra el catálogo en el ministerio.

## Lista de comprobación rápida

| Comprobación | Resultado esperado |
|---|---|
| Abrir el sitio | Página de ejemplo con aviso amarillo y botón abajo a la derecha |
| Pulsar el botón | Saludo y 4 categorías |
| Notas → boleta | Respuesta en 2 toques |
| «← Volver» desde Notas | Regresa a las categorías |
| `como saber mis notas` | ¿Cuándo y cómo puedo ver mis notas? |
| `quien gano el mundial` | Ofrece el menú |
| Escape o ✕ | Se cierra y el foco vuelve al botón |
| Teléfono | Pantalla completa, ✕ visible |
| Editor con token | Lista de preguntas |
| Editor sin token válido | No entra |
| Guardar en el editor | Commit nuevo y publicación en curso |

## Plan B

- **El sitio no carga (red del lugar):** usar el punto de acceso del teléfono.
- **GitHub Pages no responde:** en una computadora con el repositorio,
  `python entrenamiento/publicar.py --sin-entrenar` y luego
  `cd entrega && python -m http.server 8000`, y abrir `http://localhost:8000`.
- **La publicación del editor tarda o falla:** mostrar la ejecución en
  *Actions* (el sitio no cambia si falla, que es justo lo que se quiere
  mostrar) y la versión anterior sigue en línea.

## Preguntas probables

- **¿Cuánto cuesta operarlo?** Lo mismo que alojar archivos estáticos: no hay
  cálculo en el servidor.
- **¿Qué pasa si el modelo no carga?** El menú funciona igual.
- **¿Se puede equivocar?** Sí; por eso no responde ante la duda, y cada
  publicación se prueba con consultas reales antes de salir.
- **¿Quién puede cambiar las respuestas?** Solo cuentas autorizadas en GitHub;
  cada cambio queda registrado con su autor.
- **¿Funciona en el sitio del ministerio?** Sí: es una carpeta de archivos
  estáticos y una línea de código (`integracion.md`).
