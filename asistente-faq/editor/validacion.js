/*
 * Validacion del catalogo en el editor.
 *
 * GEMELA de entrenamiento/validar.py: mismas reglas, para que el editor avise
 * antes de guardar lo mismo que la publicacion rechazaria despues. La
 * autoridad sigue siendo validar.py (corre en GitHub antes de publicar);
 * pruebas/test_validacion_gemela.py compara las dos sobre los mismos casos.
 *
 * Usa normalizar() de preprocesamiento.js, igual que el entrenamiento.
 */

const PATRONES_MINIMOS = 4;
const ID_RESERVADO = "fuera-de-alcance";

function estaActiva(intencion) {
  return intencion.activa !== false;
}

function vacio(valor) {
  return valor === undefined || valor === null || String(valor).trim() === "";
}

/* Devuelve { errores, avisos }: listas de { id, texto }. `id` es el de la
 * intencion afectada, o null si el problema es del catalogo entero. */
function validarCatalogo(datos, ajenas = [], normalizarFn = normalizar) {
  const errores = [];
  const avisos = [];
  const error = (id, texto) => errores.push({ id, texto });
  const aviso = (id, texto) => avisos.push({ id, texto });

  const categorias = new Set((datos.categorias || []).map((c) => c.id));
  if (categorias.size === 0) error(null, "No hay categorías definidas.");

  const intenciones = datos.intenciones || [];
  if (intenciones.length === 0) {
    error(null, "No hay preguntas definidas.");
    return { errores, avisos };
  }

  const veces = new Map();
  for (const i of intenciones) veces.set(i.id, (veces.get(i.id) || 0) + 1);
  for (const [id, n] of veces) {
    if (n > 1) error(id, `El identificador '${id}' aparece ${n} veces.`);
  }

  if (intenciones.some((i) => i.id === ID_RESERVADO)) {
    error(ID_RESERVADO, `El identificador '${ID_RESERVADO}' está reservado para el modelo.`);
  }

  if (!intenciones.some(estaActiva)) {
    error(null, "Todas las preguntas están retiradas: debe quedar al menos una activa.");
  }

  // Patrones repetidos entre preguntas distintas: el modelo aprenderia mal ambas.
  const ubicacion = new Map();
  for (const i of intenciones) {
    if (!estaActiva(i)) continue;
    for (const patron of i.patrones || []) {
      const clave = normalizarFn(patron).join(" ");
      if (!clave) {
        aviso(i.id, `El patrón «${patron}» no aporta nada: solo tiene palabras muy comunes.`);
        continue;
      }
      if (ubicacion.has(clave) && ubicacion.get(clave) !== i.id) {
        error(i.id, `El patrón «${patron}» es igual a uno de '${ubicacion.get(clave)}'.`);
      }
      ubicacion.set(clave, i.id);
    }
  }

  for (const consulta of ajenas) {
    const clave = normalizarFn(consulta).join(" ");
    if (clave && ubicacion.has(clave)) {
      error(
        ubicacion.get(clave),
        `Un patrón coincide con la consulta fuera de alcance «${consulta}». ` +
          "Avise al equipo técnico para quitarla de fuera-de-alcance.json."
      );
    }
  }

  for (const i of intenciones) {
    const id = i.id || "(sin id)";
    for (const [campo, nombre] of [["id", "identificador"], ["categoria", "categoría"],
                                   ["pregunta", "pregunta"], ["respuesta", "respuesta"]]) {
      if (vacio(i[campo])) error(id, `Falta la ${nombre}.`);
    }

    const prioridad = i.prioridad === undefined ? 1 : i.prioridad;
    if (typeof prioridad !== "number" || !Number.isInteger(prioridad) || prioridad < 1) {
      error(id, "La prioridad debe ser un número entero desde 1.");
    }

    if ("activa" in i && typeof i.activa !== "boolean") {
      error(id, "'activa' debe ser verdadero o falso.");
    }

    if (i.respuesta !== undefined && typeof i.respuesta !== "string") {
      error(id, "La respuesta debe ser un solo texto.");
    }

    if (!categorias.has(i.categoria)) {
      error(id, `La categoría '${i.categoria}' no existe.`);
    }

    if (!estaActiva(i)) continue;

    const patrones = i.patrones || [];
    if (patrones.length === 0) {
      aviso(id, "No tiene patrones: aparece en el menú, pero el asistente no la reconoce al escribirla.");
    } else if (patrones.length < PATRONES_MINIMOS) {
      error(id, `Tiene ${patrones.length} patrones: agregue al menos ${PATRONES_MINIMOS} o déjela sin patrones.`);
    }

    if (new Set(patrones).size !== patrones.length) {
      aviso(id, "Tiene patrones repetidos.");
    }
  }

  return { errores, avisos };
}

// Exportacion doble: navegador (global) y Node (pruebas).
if (typeof module !== "undefined" && module.exports) {
  module.exports = { validarCatalogo, estaActiva, PATRONES_MINIMOS, ID_RESERVADO };
}
