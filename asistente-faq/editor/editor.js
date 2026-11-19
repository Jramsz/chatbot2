/*
 * Editor del catalogo para administradores.
 *
 * Lee contenido/intenciones.json del repositorio, permite agregar, editar,
 * retirar y reactivar preguntas con formularios (sin tocar JSON) y guarda el
 * resultado como un commit. La publicacion automatica valida, entrena y
 * despliega; si algo falla, no se publica y el sitio sigue como estaba.
 *
 * Nunca se borra una pregunta: se retira con "activa": false, para que su
 * identificador quede reservado (convencion del proyecto).
 *
 * Todo texto del catalogo se pinta con textContent, nunca como HTML.
 */

const Editor = (() => {
  const CLAVE_TOKEN = "asistente-faq:token-editor";
  const NUEVA = "__nueva__";

  let config, token;
  let datos = null;       // el catalogo en edicion
  let ajenas = [];        // consultas fuera de alcance, para las colisiones
  let sha = null;         // version leida: GitHub rechaza guardar sobre otra
  let sucio = false;
  let editando = null;    // id de la pregunta abierta, o NUEVA
  let idTocado = false;   // el administrador escribio el id a mano
  let cambios;
  let temporizador = null;

  const $ = (id) => document.getElementById(id);

  function reiniciarCambios() {
    cambios = { agregadas: new Set(), editadas: new Set(), retiradas: new Set(), reactivadas: new Set() };
  }
  reiniciarCambios();

  // ---- Utilidades ----

  function estado(texto, esError = false) {
    $("estado").textContent = texto;
    $("estado").classList.toggle("error", esError);
  }

  function guardarToken(t) { try { sessionStorage.setItem(CLAVE_TOKEN, t); } catch (e) { /* sin almacenamiento */ } }
  function leerToken() { try { return sessionStorage.getItem(CLAVE_TOKEN); } catch (e) { return null; } }
  function borrarToken() { try { sessionStorage.removeItem(CLAVE_TOKEN); } catch (e) { /* nada */ } }

  function sinAcentos(texto) {
    return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function elemento(etiqueta, clase, texto) {
    const e = document.createElement(etiqueta);
    if (clase) e.className = clase;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }

  function boton(texto, clase, accion, etiquetaAccesible) {
    const b = elemento("button", clase, texto);
    b.type = "button";
    if (etiquetaAccesible) b.setAttribute("aria-label", etiquetaAccesible);
    b.addEventListener("click", accion);
    return b;
  }

  function buscarIntencion(id) {
    return datos.intenciones.find((i) => i.id === id);
  }

  function validar(catalogo = datos) {
    return validarCatalogo(catalogo, ajenas);
  }

  // ---- Sesion ----

  async function ingresar(t) {
    estado("Comprobando el acceso…");
    const acceso = await GitHub.comprobarAcceso(t, config.repositorio);
    if (!acceso.puedeEscribir) {
      throw new GitHub.ErrorGitHub(403,
        `La cuenta ${acceso.usuario} no tiene permiso de escritura en ${config.repositorio}.`);
    }
    token = t;
    guardarToken(t);
    $("usuario").textContent = acceso.usuario;
    $("sesion").hidden = false;
    $("ingreso").hidden = true;
    $("editor").hidden = false;
    await recargar();
  }

  function salir() {
    if (sucio && !confirm("Hay cambios sin guardar. ¿Salir de todos modos?")) return;
    clearTimeout(temporizador);
    borrarToken();
    token = null;
    datos = null;
    sucio = false;
    $("sesion").hidden = true;
    $("editor").hidden = true;
    $("ingreso").hidden = false;
    $("token").value = "";
    estado("Sesión cerrada.");
  }

  async function recargar() {
    if (sucio && !confirm("Se perderán los cambios sin guardar. ¿Recargar?")) return;
    estado("Cargando el catálogo…");
    const [catalogo, fuera] = await Promise.all([
      GitHub.leerArchivo(token, config.repositorio, config.rama, config.catalogo),
      GitHub.leerArchivo(token, config.repositorio, config.rama, config.fueraDeAlcance).catch(() => null),
    ]);
    datos = JSON.parse(catalogo.texto);
    sha = catalogo.sha;
    ajenas = fuera ? JSON.parse(fuera.texto).consultas || [] : [];
    sucio = false;
    reiniciarCambios();
    cerrarFormulario();
    pintar();
    const activas = datos.intenciones.filter(estaActiva).length;
    estado(`Catálogo cargado: ${activas} preguntas activas de ${datos.intenciones.length}.`);
    mostrarPublicacion(await GitHub.ultimaPublicacion(token, config.repositorio, config.rama));
  }

  // ---- Lista ----

  function pintar() {
    const v = validar();
    pintarLista(v);
    pintarProblemas(v);
    $("guardar").disabled = !sucio || v.errores.length > 0;
    $("mensaje").placeholder = resumenCambios() || "Describa el cambio";
  }

  function coincide(intencion, consulta) {
    if (!consulta) return true;
    const texto = [intencion.pregunta, intencion.respuesta, ...(intencion.patrones || [])].join(" ");
    return sinAcentos(texto).includes(consulta);
  }

  function pintarLista(v) {
    const lista = $("lista");
    lista.replaceChildren();
    const filtro = $("filtro").value;
    const consulta = sinAcentos($("buscar").value.trim());
    const problemas = (tipo) => v[tipo].reduce((m, p) => m.set(p.id, (m.get(p.id) || 0) + 1), new Map());
    const errores = problemas("errores");
    const avisos = problemas("avisos");
    let mostradas = 0;

    for (const categoria of datos.categorias) {
      const preguntas = datos.intenciones
        .filter((i) => i.categoria === categoria.id)
        .filter((i) => filtro === "todas" || (filtro === "activas") === estaActiva(i))
        .filter((i) => coincide(i, consulta))
        .sort((a, b) => (a.subtema || "").localeCompare(b.subtema || "") || (a.prioridad || 99) - (b.prioridad || 99));
      if (!preguntas.length) continue;

      lista.appendChild(elemento("h3", null, categoria.nombre));
      for (const i of preguntas) {
        mostradas++;
        const fila = elemento("div", "pregunta");
        fila.classList.toggle("retirada", !estaActiva(i));
        fila.classList.toggle("seleccionada", editando === i.id);

        const texto = elemento("span", "texto", i.pregunta);
        const n = (i.patrones || []).length;
        texto.appendChild(elemento("span", "detalle",
          `${i.subtema || "sin subtema"} · ${n} patrones${estaActiva(i) ? "" : " · retirada"}`));
        if (errores.get(i.id)) texto.appendChild(elemento("span", "marca error", `${errores.get(i.id)} error(es)`));
        if (avisos.get(i.id)) texto.appendChild(elemento("span", "marca aviso", `${avisos.get(i.id)} aviso(s)`));
        fila.appendChild(texto);

        fila.appendChild(boton("Editar", "secundario", () => abrir(i.id), `Editar «${i.pregunta}»`));
        fila.appendChild(estaActiva(i)
          ? boton("Retirar", "peligro", () => retirar(i.id), `Retirar «${i.pregunta}»`)
          : boton("Reactivar", "secundario", () => reactivar(i.id), `Reactivar «${i.pregunta}»`));
        lista.appendChild(fila);
      }
    }
    if (!mostradas) lista.appendChild(elemento("p", "nota", "No hay preguntas que coincidan."));
  }

  function pintarProblemas(v) {
    const ul = $("problemas");
    ul.replaceChildren();
    if (!v.errores.length && !v.avisos.length) {
      ul.appendChild(elemento("li", "ok", "Sin problemas: el catálogo se puede guardar."));
      return;
    }
    for (const [tipo, lista] of [["error", v.errores], ["aviso", v.avisos]]) {
      for (const p of lista) {
        const li = elemento("li", tipo, p.texto);
        if (p.id && buscarIntencion(p.id)) li.appendChild(boton("Ver", "secundario", () => abrir(p.id)));
        ul.appendChild(li);
      }
    }
  }

  // ---- Formulario ----

  function pintarCategorias(seleccion) {
    const select = $("fCategoria");
    select.replaceChildren();
    for (const c of datos.categorias) {
      const op = elemento("option", null, c.nombre);
      op.value = c.id;
      select.appendChild(op);
    }
    select.value = seleccion || datos.categorias[0].id;
    pintarSubtemas();
  }

  function pintarSubtemas() {
    const lista = $("subtemas");
    lista.replaceChildren();
    const usados = new Set(datos.intenciones
      .filter((i) => i.categoria === $("fCategoria").value).map((i) => i.subtema).filter(Boolean));
    for (const s of usados) {
      const op = document.createElement("option");
      op.value = s;
      lista.appendChild(op);
    }
  }

  function contarPatrones() {
    $("contadorPatrones").textContent = String(leerPatrones().length);
  }

  function leerPatrones() {
    return $("fPatrones").value.split("\n").map((p) => p.trim()).filter(Boolean);
  }

  function abrir(id) {
    const i = buscarIntencion(id);
    editando = id;
    $("tituloFormulario").textContent = "Editar pregunta";
    $("fPregunta").value = i.pregunta || "";
    $("fRespuesta").value = i.respuesta || "";
    pintarCategorias(i.categoria);
    $("fSubtema").value = i.subtema || "";
    $("fPrioridad").value = i.prioridad || 1;
    $("fPatrones").value = (i.patrones || []).join("\n");
    $("fId").value = i.id;
    $("fId").readOnly = true;
    mostrarFormulario();
  }

  function nueva() {
    editando = NUEVA;
    idTocado = false;
    $("tituloFormulario").textContent = "Agregar pregunta";
    $("formPregunta").reset();
    pintarCategorias();
    $("fPrioridad").value = 1;
    $("fId").readOnly = false;
    mostrarFormulario();
  }

  function mostrarFormulario() {
    $("erroresPregunta").replaceChildren();
    contarPatrones();
    $("formulario").hidden = false;
    pintar();
    $("fPregunta").focus();
  }

  function cerrarFormulario() {
    editando = null;
    $("formulario").hidden = true;
    if (datos) pintar();
  }

  // Identificador sugerido para una pregunta nueva: prefijo de su categoria
  // (el que ya usan sus preguntas) y las palabras significativas.
  function sugerirId() {
    const categoria = $("fCategoria").value;
    const prefijos = datos.intenciones.filter((i) => i.categoria === categoria).map((i) => i.id.split("-")[0]);
    const prefijo = prefijos.sort((a, b) => prefijos.filter((x) => x === b).length - prefijos.filter((x) => x === a).length)[0] || categoria;
    const interrogativas = new Set(["como", "donde", "cuando", "cual", "cuales", "quien", "puedo", "hago"]);
    const palabras = sinAcentos($("fPregunta").value).replace(/[^a-z0-9]+/g, " ").split(" ")
      .filter((p) => p.length > 3 && !interrogativas.has(p)).slice(0, 4);
    const base = [prefijo, ...palabras].join("-");
    let id = base;
    for (let n = 2; buscarIntencion(id); n++) id = `${base}-${n}`;
    return id;
  }

  function aplicar(evento) {
    evento.preventDefault();
    const nuevaPregunta = editando === NUEVA;
    const anterior = nuevaPregunta ? {} : buscarIntencion(editando);
    const intencion = {
      ...anterior,
      id: $("fId").value.trim(),
      categoria: $("fCategoria").value,
      subtema: $("fSubtema").value.trim(),
      prioridad: Number($("fPrioridad").value),
      pregunta: $("fPregunta").value.trim(),
      respuesta: $("fRespuesta").value.trim(),
      patrones: leerPatrones(),
    };
    if (nuevaPregunta) intencion.vigencia = "permanente";

    // Se prueba el cambio sobre una copia: solo se aplica si no agrega errores.
    const copia = structuredClone(datos);
    if (nuevaPregunta) copia.intenciones.push(intencion);
    else copia.intenciones[datos.intenciones.indexOf(anterior)] = intencion;
    const previos = new Set(validar().errores.map((e) => e.texto));
    const nuevos = validar(copia).errores.filter((e) => !previos.has(e.texto));
    if (nuevaPregunta && !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(intencion.id)) {
      nuevos.unshift({ texto: "El identificador solo puede tener minúsculas, números y guiones." });
    }

    const ul = $("erroresPregunta");
    ul.replaceChildren();
    if (nuevos.length) {
      for (const e of nuevos) ul.appendChild(elemento("li", "error", e.texto));
      estado("El cambio no se aplicó: corrija lo indicado en el formulario.", true);
      return;
    }

    datos = copia;
    if (nuevaPregunta) cambios.agregadas.add(intencion.id);
    else if (!cambios.agregadas.has(intencion.id)) cambios.editadas.add(intencion.id);
    sucio = true;
    cerrarFormulario();
    estado(`«${intencion.pregunta}» ${nuevaPregunta ? "agregada" : "actualizada"}. Recuerde guardar y publicar.`);
  }

  function retirar(id) {
    const i = buscarIntencion(id);
    if (!confirm(`¿Retirar «${i.pregunta}»? Dejará de aparecer en el asistente. Se puede reactivar después.`)) return;
    const copia = structuredClone(datos);
    copia.intenciones.find((x) => x.id === id).activa = false;
    if (validar(copia).errores.some((e) => e.id === null)) {
      estado("No se puede retirar: debe quedar al menos una pregunta activa.", true);
      return;
    }
    i.activa = false;
    if (!cambios.reactivadas.delete(id)) cambios.retiradas.add(id);
    sucio = true;
    if (editando === id) cerrarFormulario(); else pintar();
    estado(`«${i.pregunta}» retirada. Su identificador queda reservado. Recuerde guardar y publicar.`);
  }

  function reactivar(id) {
    const i = buscarIntencion(id);
    delete i.activa;
    if (!cambios.retiradas.delete(id)) cambios.reactivadas.add(id);
    sucio = true;
    pintar();
    estado(`«${i.pregunta}» reactivada. Recuerde guardar y publicar.`);
  }

  // ---- Guardar ----

  function resumenCambios() {
    const partes = [];
    const nombres = (ids) => [...ids].join(", ");
    if (cambios.agregadas.size) partes.push(`agregar ${nombres(cambios.agregadas)}`);
    if (cambios.editadas.size) partes.push(`editar ${nombres(cambios.editadas)}`);
    if (cambios.retiradas.size) partes.push(`retirar ${nombres(cambios.retiradas)}`);
    if (cambios.reactivadas.size) partes.push(`reactivar ${nombres(cambios.reactivadas)}`);
    return partes.length ? `Catálogo: ${partes.join("; ")}` : "";
  }

  // Mismo formato que escriben los scripts de Python, para que los cambios
  // se lean bien en el historial.
  function serializar() {
    datos.actualizado = new Date().toISOString().slice(0, 10);
    const texto = JSON.stringify(datos, null, 2)
      .replace(/\{\s*"id": "([^"]+)",\s*"nombre": "([^"]+)"\s*\}/g, '{ "id": "$1", "nombre": "$2" }');
    return texto + "\n";
  }

  async function guardar() {
    if (validar().errores.length) {
      estado("Hay errores: corríjalos antes de guardar.", true);
      return;
    }
    const mensaje = $("mensaje").value.trim() || resumenCambios() || "Catálogo: cambios desde el editor";
    $("guardar").disabled = true;
    estado("Guardando en GitHub…");
    try {
      const r = await GitHub.guardarArchivo(token, config.repositorio, config.rama,
        config.catalogo, serializar(), sha, mensaje);
      sha = r.sha;
      sucio = false;
      reiniciarCambios();
      $("mensaje").value = "";
      pintar();
      estado("Guardado. La publicación automática tarda unos minutos; el estado aparece abajo.");
      seguirPublicacion(r.commitSha, Date.now());
    } catch (e) {
      estado(e.message, true);
      pintar();
    }
  }

  function descargar() {
    const url = URL.createObjectURL(new Blob([serializar()], { type: "application/json" }));
    const a = elemento("a");
    a.href = url;
    a.download = "intenciones.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  // ---- Estado de la publicacion ----

  function mostrarPublicacion(run, esperandoCommit) {
    const p = $("publicacion");
    p.replaceChildren();
    if (!run) {
      if (esperandoCommit) {
        p.textContent = "Para ver el estado de la publicación, revise la pestaña Actions del repositorio.";
      }
      return;
    }
    const textos = {
      queued: "Publicación en cola…",
      in_progress: "Publicando: validando, entrenando y desplegando…",
    };
    let texto;
    if (run.estado !== "completed") texto = textos[run.estado] || "Publicando…";
    else if (run.resultado === "success") texto = "Última publicación: correcta. El sitio está actualizado.";
    else texto = "La última publicación falló: no se publicó nada y el sitio sigue con la versión anterior.";
    p.appendChild(document.createTextNode(texto + " "));
    const enlace = elemento("a", null, "Ver detalles");
    enlace.href = run.url;
    enlace.target = "_blank";
    enlace.rel = "noopener";
    p.appendChild(enlace);
  }

  function seguirPublicacion(commitSha, inicio) {
    clearTimeout(temporizador);
    temporizador = setTimeout(async () => {
      if (!token) return;
      const run = await GitHub.ultimaPublicacion(token, config.repositorio, config.rama);
      const propia = run && run.sha === commitSha;
      mostrarPublicacion(propia ? run : null, true);
      const terminada = propia && run.estado === "completed";
      if (!terminada && Date.now() - inicio < 30 * 60 * 1000) seguirPublicacion(commitSha, inicio);
    }, 15000);
  }

  // ---- Inicio ----

  async function iniciar() {
    try {
      config = await (await fetch("config.json", { cache: "no-cache" })).json();
    } catch (e) {
      estado("No se pudo leer config.json del editor.", true);
      return;
    }

    $("formIngreso").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await ingresar($("token").value.trim());
      } catch (err) {
        borrarToken();
        estado(err.message, true);
      }
    });
    $("salir").addEventListener("click", salir);
    $("buscar").addEventListener("input", () => pintar());
    $("filtro").addEventListener("change", () => pintar());
    $("agregar").addEventListener("click", nueva);
    $("cancelar").addEventListener("click", cerrarFormulario);
    $("formPregunta").addEventListener("submit", aplicar);
    $("fCategoria").addEventListener("change", () => {
      pintarSubtemas();
      if (editando === NUEVA && !idTocado) $("fId").value = sugerirId();
    });
    $("fPregunta").addEventListener("input", () => {
      if (editando === NUEVA && !idTocado) $("fId").value = sugerirId();
    });
    $("fId").addEventListener("input", () => { idTocado = true; });
    $("fPatrones").addEventListener("input", contarPatrones);
    $("guardar").addEventListener("click", guardar);
    $("descargar").addEventListener("click", descargar);
    $("recargar").addEventListener("click", () => recargar().catch((e) => estado(e.message, true)));
    window.addEventListener("beforeunload", (e) => {
      if (sucio) { e.preventDefault(); e.returnValue = ""; }
    });

    const guardado = leerToken();
    if (guardado) {
      try {
        await ingresar(guardado);
      } catch (e) {
        borrarToken();
        estado(e.message, true);
      }
    }
  }

  return { iniciar };
})();

document.addEventListener("DOMContentLoaded", Editor.iniciar);
