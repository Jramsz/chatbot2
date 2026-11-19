# Editor del catálogo (administradores)

Página para agregar, editar, retirar y reactivar preguntas sin tocar archivos.
Está en la carpeta `editor/` del sitio publicado; por ejemplo, en la
demostración: `https://jramsz.github.io/chatbot2/editor/`.

## Quién puede usarlo

Solo las personas con **permiso de escritura en el repositorio** del asistente
en GitHub. El acceso lo controla GitHub, no la página: sin ese permiso no se
puede leer el catálogo ni guardar nada. Por eso no hay usuario y contraseña
propios; se ingresa con un **token de acceso** de GitHub.

Para dar acceso a una persona, el dueño del repositorio la agrega en
*Settings → Collaborators* con permiso de escritura.

## Crear el token (una vez, o cuando venza)

1. En GitHub, abra *Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token*
   (enlace directo: https://github.com/settings/personal-access-tokens/new).
2. **Token name:** por ejemplo «Editor del asistente».
3. **Expiration:** 90 días (al vencer, se crea otro igual).
4. **Repository access:** *Only select repositories* y elija el repositorio
   del asistente.
5. **Permissions → Repository permissions:**
   - *Contents*: **Read and write** (necesario para guardar).
   - *Actions*: **Read-only** (opcional: permite ver en el editor si la
     publicación terminó).
6. *Generate token* y copie el valor. GitHub no lo vuelve a mostrar.

**El token equivale a una contraseña.** No lo comparta ni lo pegue en correos
o chats. Si se filtra, revóquelo en la misma página de GitHub y cree otro. El
editor lo guarda solo en la pestaña abierta y lo borra al cerrarla.

## Usar el editor

1. Abra el editor, pegue el token y pulse **Ingresar**.
2. Busque la pregunta o use el filtro (activas, retiradas, todas).
3. **Editar:** cambie lo necesario y pulse **Aplicar**.
4. **Agregar pregunta:** complete pregunta, respuesta, categoría, subtema,
   orden y las formas de preguntarlo (una por línea). El identificador se
   propone solo; revíselo, porque después no se puede cambiar.
5. **Retirar:** la pregunta deja de aparecer en el asistente, pero no se
   borra: su identificador queda reservado y se puede **Reactivar**.
6. Revise el recuadro **Guardar y publicar**: si hay errores, se indican y no
   se puede guardar hasta corregirlos. Los avisos no impiden guardar.
7. Pulse **Guardar y publicar**. El cambio queda registrado en GitHub a su
   nombre, con la descripción indicada (o una automática).

Los cambios aplicados quedan solo en su navegador hasta pulsar **Guardar y
publicar**. Si intenta cerrar la página con cambios sin guardar, el navegador
le avisa.

## Después de guardar

La publicación es automática y tarda unos minutos: valida el catálogo, entrena
el modelo, comprueba las pruebas de aceptación y actualiza el sitio. El editor
muestra el estado si el token tiene permiso de lectura de *Actions*.

- **Si algo falla, no se publica nada**: el sitio sigue con la versión
  anterior. Pulse «Ver detalles» o avise al equipo técnico.
- Si solo cambió textos, el asistente los muestra en cuanto termina la
  publicación. Las preguntas nuevas aparecen en el menú; reconocerlas al
  escribirlas depende de sus patrones.

## Reglas que el editor hace cumplir

- Toda pregunta necesita pregunta, respuesta, categoría y orden.
- Una pregunta activa tiene **al menos 4 formas de preguntarlo, o ninguna**
  (sin ninguna, solo aparece en el menú).
- Dos preguntas no pueden tener la misma forma de preguntarlo.
- Las preguntas no se borran: se retiran.
- Debe quedar al menos una pregunta activa.

## Situaciones comunes

| Mensaje | Qué hacer |
|---|---|
| «El token no es válido o ya venció» | Cree un token nuevo. |
| «No tiene permiso de escritura» | Pida al dueño del repositorio que lo agregue como colaborador. |
| «Alguien guardó cambios mientras usted editaba» | Pulse **Recargar desde GitHub** y repita sus cambios sobre la versión actual. |
| La publicación falló | No se publicó nada. Avise al equipo técnico con el enlace «Ver detalles». |

**Sin acceso a GitHub:** el botón **Descargar intenciones.json** guarda el
catálogo editado como archivo, para entregarlo al equipo técnico.
