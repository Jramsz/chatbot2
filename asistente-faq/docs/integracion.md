# Guía de integración del asistente

Para el personal técnico que publica el asistente en un sitio web.

## Qué se recibe

Una carpeta `asistente/` con archivos estáticos (HTML, CSS, JavaScript, el
catálogo y el modelo). No necesita base de datos, lenguaje de servidor ni
configuración: cualquier servidor que entregue archivos sirve.

## 1. Alojar la carpeta

Copie la carpeta `asistente/` completa a cualquier ubicación pública del
servidor web, por ejemplo `https://sitio.ejemplo/asistente/`. Puede estar en un
subdirectorio o en otro dominio: no hay rutas fijas.

Compruebe que `https://sitio.ejemplo/asistente/index.html` abre el asistente.

## 2. Insertarlo en las páginas

Agregue esta línea antes de `</body>` en cada página donde deba aparecer:

```html
<script src="https://sitio.ejemplo/asistente/insertar.js" defer></script>
```

Aparece un botón en la esquina inferior derecha que abre el asistente en un
marco. En teléfonos, el marco ocupa toda la pantalla. El asistente no se
descarga hasta que alguien pulsa el botón, así que no hace más lenta la página.

Alternativa sin JavaScript en la página anfitriona: un marco fijo.

```html
<iframe src="https://sitio.ejemplo/asistente/index.html"
        title="Asistente de preguntas frecuentes"
        style="width: 100%; max-width: 420px; height: 560px; border: none;"></iframe>
```

## 3. Si el sitio tiene política de seguridad de contenido (CSP)

Si el asistente está en otro dominio que el sitio, la política del sitio debe
permitir ese dominio en `script-src` (para `insertar.js`) y en `frame-src`
(para el marco). El asistente no carga nada de terceros: TensorFlow.js va
incluido en `asistente/lib/`.

## Actualizar el contenido

| Qué cambió | Qué se publica |
|---|---|
| Texto de preguntas o respuestas, preguntas solo de menú | Solo `asistente/datos/catalogo.json` |
| Patrones (lo que el asistente reconoce al escribir) | La carpeta `asistente/` completa |

Detalles en `manual-actualizacion.md`. Los archivos se piden siempre con
revalidación, así que los cambios se ven sin que el visitante borre su caché.

## Comprobación rápida después de publicar

1. Abrir una página con el botón y pulsarlo: aparece el saludo y el menú.
2. Escribir «se me perdió la boleta de notas»: responde sobre la reposición.
3. Escribir «quién va a ganar el mundial»: no responde, ofrece el menú.
4. Repetir 1 y 2 desde un teléfono.
