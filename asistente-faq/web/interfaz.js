/*
 * Interfaz del asistente. Toda cadena visible para el usuario esta en TEXTOS,
 * no repartida por el codigo, para poder ajustar la redaccion sin tocar logica.
 */

const TEXTOS = {
  bienvenida:
    "Hola. Puedo ayudarte con consultas sobre trámites, notas y útiles escolares. " +
    "Escribe tu pregunta o elige una categoría.",
  elegirCategoria: "¿Sobre qué tema necesitas información?",
  elegirSubtema: "Elige una opción:",
  elegirPregunta: "¿Cuál de estas preguntas es la tuya?",
  sinConfianza:
    "No estoy seguro de haber entendido tu consulta, y prefiero no darte " +
    "información equivocada. Busquemos por categoría:",
  sinTerminos:
    "No reconocí ninguna palabra de tu consulta. Probemos por categoría:",
  sinModelo: "Elige una categoría para encontrar tu respuesta:",
  modeloCargando:
    "Todavía estoy preparando la búsqueda por texto. Mientras tanto, " +
    "elige una categoría:",
  errorCarga:
    "No se pudo cargar el asistente. Recarga la página o inténtalo más tarde.",
  volver: "← Volver",
  inicio: "Menú principal",
  otraConsulta: "Hacer otra consulta",
};

const Interfaz = (() => {
  let conversacion, entrada, boton, anuncio;

  function burbuja(texto, quien) {
    const div = document.createElement("div");
    div.className = `burbuja ${quien}`;
    div.textContent = texto;
    conversacion.appendChild(div);
    if (quien === "bot") anunciar(texto);
    desplazar();
    return div;
  }

  // Lo que dice el asistente se anuncia al lector de pantalla. Se vacia antes
  // de escribir para que un mensaje repetido tambien se lea.
  function anunciar(texto) {
    anuncio.textContent = "";
    requestAnimationFrame(() => { anuncio.textContent = texto; });
  }

  function opciones(lista) {
    const cont = document.createElement("div");
    cont.className = "opciones";
    for (const { etiqueta, accion } of lista) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "opcion";
      b.textContent = etiqueta;
      b.addEventListener("click", () => {
        // Se desactivan las opciones ya usadas para que el historial de la
        // conversacion quede legible y no se pueda volver a un estado previo
        // por error.
        cont.querySelectorAll("button").forEach((x) => (x.disabled = true));
        burbuja(etiqueta, "usuario");
        accion();
        // El boton pulsado queda deshabilitado y el navegador saca el foco a
        // la pagina: quien usa teclado o lector de pantalla perderia su
        // posicion. Se lleva el foco a la primera opcion nueva.
        const nuevas = conversacion.lastElementChild;
        const primera = nuevas && nuevas.querySelector("button:not(:disabled)");
        if (primera) primera.focus();
      });
      cont.appendChild(b);
    }
    conversacion.appendChild(cont);
    desplazar();
  }

  function desplazar() {
    conversacion.scrollTop = conversacion.scrollHeight;
  }

  // ---- Flujo de navegacion por menu ----

  function mostrarCategorias(mensaje) {
    burbuja(mensaje || TEXTOS.elegirCategoria, "bot");
    opciones(
      Motor.categorias().map((c) => ({
        etiqueta: c.nombre,
        accion: () => mostrarSubtemas(c.id),
      }))
    );
  }

  function mostrarSubtemas(idCategoria) {
    const lista = Motor.subtemas(idCategoria);

    // Con un solo subtema, el nivel intermedio no aporta nada: se salta.
    if (lista.length === 1) {
      mostrarPreguntas(idCategoria, lista[0]);
      return;
    }

    burbuja(TEXTOS.elegirSubtema, "bot");
    opciones([
      ...lista.map((s) => ({
        etiqueta: s,
        accion: () => mostrarPreguntas(idCategoria, s),
      })),
      { etiqueta: TEXTOS.volver, accion: () => mostrarCategorias() },
    ]);
  }

  function mostrarPreguntas(idCategoria, subtema) {
    // Si la categoria tiene un solo subtema, ese nivel se salto al entrar:
    // volver a el reabriria esta misma lista y el usuario quedaria atrapado.
    const volver = Motor.subtemas(idCategoria).length === 1
      ? () => mostrarCategorias()
      : () => mostrarSubtemas(idCategoria);

    burbuja(TEXTOS.elegirPregunta, "bot");
    opciones([
      ...Motor.preguntas(idCategoria, subtema).map((i) => ({
        etiqueta: i.pregunta,
        accion: () => responder(i),
      })),
      { etiqueta: TEXTOS.volver, accion: volver },
    ]);
  }

  function responder(intencion) {
    burbuja(intencion.respuesta, "bot");
    opciones([
      { etiqueta: TEXTOS.otraConsulta, accion: () => mostrarCategorias() },
    ]);
  }

  // ---- Consulta escrita libremente ----

  function enviar() {
    const texto = entrada.value.trim();
    if (!texto) return;
    entrada.value = "";
    burbuja(texto, "usuario");

    const r = Motor.clasificar(texto);

    if (r.estado === "respuesta" && r.intencion) {
      responder(r.intencion);
      return;
    }

    const mensaje =
      r.estado === "sin_terminos" ? TEXTOS.sinTerminos
      : r.estado === "sin_modelo" && Motor.estadoModelo() === "cargando"
        ? TEXTOS.modeloCargando
      : r.estado === "sin_modelo" ? TEXTOS.sinModelo
      : TEXTOS.sinConfianza;

    mostrarCategorias(mensaje);
  }

  async function iniciar() {
    // Dentro del marco de insertar.js el asistente ocupa todo el marco; abierto
    // directamente conserva su caja centrada.
    if (window.self !== window.top) {
      document.body.classList.add("embebido");
      // Las teclas pulsadas dentro del marco no llegan a la pagina anfitriona:
      // se le avisa para que Escape cierre el asistente tambien desde aqui.
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") window.parent.postMessage({ tipo: "asistente-faq:cerrar" }, "*");
      });
    }

    conversacion = document.getElementById("conversacion");
    entrada = document.getElementById("entrada");
    boton = document.getElementById("enviar");
    anuncio = document.getElementById("anuncio");

    boton.addEventListener("click", enviar);
    entrada.addEventListener("keydown", (e) => {
      if (e.key === "Enter") enviar();
    });

    try {
      await Motor.iniciar();
    } catch (e) {
      console.error(e);
      burbuja(TEXTOS.errorCarga, "bot");
      return;
    }

    burbuja(TEXTOS.bienvenida, "bot");
    mostrarCategorias();

    // El modelo se carga en segundo plano: el menu ya es utilizable.
    entrada.disabled = false;
    Motor.cargarModelo();
  }

  return { iniciar };
})();

document.addEventListener("DOMContentLoaded", Interfaz.iniciar);
