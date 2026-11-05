/*
 * Inserta el asistente en cualquier pagina con una sola linea:
 *
 *   <script src="https://<donde-este-alojado>/insertar.js" defer></script>
 *
 * Agrega un boton flotante que abre el asistente en un marco (iframe). La
 * direccion del asistente se deduce de la de este archivo: no hay dominios
 * fijos, el ministerio puede alojarlo donde quiera (invariante 7).
 *
 * No depende de nada del sitio anfitrion. Sus estilos usan el prefijo
 * "asistente-faq-" para no chocar con los del sitio.
 */

(() => {
  const TEXTOS = {
    abrir: "¿Tienes dudas? Pregunta aquí",
    cerrar: "Cerrar el asistente",
    tituloMarco: "Asistente de preguntas frecuentes",
  };

  const script = document.currentScript;
  if (!script) return;   // cargado de una forma no soportada (p. ej. como modulo)
  const destino = new URL("index.html", script.src).href;

  const estilos = document.createElement("style");
  estilos.textContent = `
    .asistente-faq-boton {
      position: fixed; right: 16px; bottom: 16px; z-index: 2147483001;
      padding: 12px 18px; border: none; border-radius: 24px;
      font: 600 15px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      color: #fff; background: #1f3864; cursor: pointer;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    }
    .asistente-faq-boton:focus-visible { outline: 3px solid #f2b705; outline-offset: 2px; }
    /* El boton queda por encima del marco: en el telefono el marco ocupa
       toda la pantalla y el boton es la unica forma de cerrarlo. */
    .asistente-faq-marco {
      position: fixed; right: 16px; bottom: 76px; z-index: 2147483000;
      width: 380px; height: 560px; max-height: calc(100vh - 96px);
      border: none; border-radius: 12px; background: #fff;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
    }
    .asistente-faq-marco[hidden] { display: none; }
    @media (max-width: 520px) {
      .asistente-faq-marco {
        right: 0; bottom: 0; width: 100vw; height: 100vh;
        max-height: none; border-radius: 0;
      }
      .asistente-faq-boton.abierto { top: 8px; bottom: auto; right: 8px; }
    }
  `;

  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "asistente-faq-boton";
  boton.textContent = TEXTOS.abrir;
  boton.setAttribute("aria-expanded", "false");
  boton.setAttribute("aria-controls", "asistente-faq-marco");

  // El marco se crea al primer clic: el sitio anfitrion no descarga el
  // asistente (ni el modelo) si nadie lo abre.
  let marco = null;

  function alternar(abrir) {
    if (abrir && !marco) {
      marco = document.createElement("iframe");
      marco.id = "asistente-faq-marco";
      marco.className = "asistente-faq-marco";
      marco.title = TEXTOS.tituloMarco;
      marco.src = destino;
      document.body.appendChild(marco);
    }
    if (marco) marco.hidden = !abrir;
    boton.textContent = abrir ? "✕" : TEXTOS.abrir;
    boton.setAttribute("aria-label", abrir ? TEXTOS.cerrar : TEXTOS.abrir);
    boton.setAttribute("aria-expanded", String(abrir));
    boton.classList.toggle("abierto", abrir);
    if (abrir) marco.focus();
  }

  boton.addEventListener("click", () => alternar(boton.getAttribute("aria-expanded") !== "true"));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && boton.getAttribute("aria-expanded") === "true") {
      alternar(false);
      boton.focus();
    }
  });

  function montar() {
    document.head.appendChild(estilos);
    document.body.appendChild(boton);
  }
  if (document.body) montar();
  else document.addEventListener("DOMContentLoaded", montar);
})();
