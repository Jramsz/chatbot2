/*
 * Motor del asistente: carga el modelo, clasifica consultas y navega el catalogo.
 *
 * Esta capa no conoce la interfaz. Expone datos y funciones; interfaz.js decide
 * como mostrarlos. Esa separacion permite reutilizar el motor en otro canal sin
 * tocar la logica.
 */

// Por debajo de este valor el asistente NO responde: deriva al menu.
// Para una institucion publica, informar mal es peor que no responder.
const UMBRAL_CONFIANZA = 0.75;

const Motor = (() => {
  let catalogo = null;      // categorias e intenciones con sus respuestas
  let vocabulario = null;   // orden fijado en el entrenamiento
  let clases = null;        // orden fijado en el entrenamiento
  let modelo = null;        // puede quedar en null: el menu sigue funcionando
  let porId = new Map();

  async function cargarJson(ruta) {
    const r = await fetch(ruta);
    if (!r.ok) throw new Error(`No se pudo cargar ${ruta} (${r.status})`);
    return r.json();
  }

  /* Carga el catalogo primero y el modelo despues.
   * El orden importa: en cuanto el catalogo esta listo el menu ya sirve,
   * asi que el usuario puede empezar a navegar mientras el modelo descarga. */
  async function iniciar() {
    [catalogo, vocabulario, clases] = await Promise.all([
      cargarJson("datos/catalogo.json"),
      cargarJson("datos/vocabulario.json"),
      cargarJson("datos/clases.json"),
    ]);

    porId = new Map(catalogo.intenciones.map((i) => [i.id, i]));
    return { menuListo: true };
  }

  /* Carga diferida del modelo. Si falla, el asistente sigue operando en modo
   * menu; se registra el fallo pero no se interrumpe el servicio. */
  async function cargarModelo() {
    try {
      modelo = await tf.loadLayersModel("modelo/model.json");
      return true;
    } catch (e) {
      console.warn("El modelo no se pudo cargar; el asistente opera con el menu.", e);
      modelo = null;
      return false;
    }
  }

  function modeloDisponible() {
    return modelo !== null;
  }

  /* Clasifica una consulta escrita libremente.
   * Devuelve { estado, intencion, confianza }:
   *   estado "respuesta"     -> la confianza supera el umbral
   *   estado "sin_confianza" -> no alcanza el umbral, o la candidata ya no
   *                             existe en el catalogo (intencion null)
   *   estado "sin_modelo"    -> el modelo no esta disponible
   *   estado "sin_terminos"  -> la consulta no contiene ningun termino conocido
   */
  function clasificar(texto) {
    if (!modelo) return { estado: "sin_modelo" };

    const vector = bolsaDePalabras(texto, vocabulario);
    if (vector.every((v) => v === 0)) {
      return { estado: "sin_terminos" };
    }

    // tf.tidy libera los tensores intermedios; sin esto la memoria crece
    // en cada consulta.
    const { indice, confianza } = tf.tidy(() => {
      const entrada = tf.tensor2d([vector]);
      const salida = modelo.predict(entrada);
      const probabilidades = salida.dataSync();
      let mejor = 0;
      for (let n = 1; n < probabilidades.length; n++) {
        if (probabilidades[n] > probabilidades[mejor]) mejor = n;
      }
      return { indice: mejor, confianza: probabilidades[mejor] };
    });

    // El modelo puede conocer una intencion que ya no esta en el catalogo
    // (se retiro la pregunta y aun no se reentrena). No hay respuesta que
    // entregar: se trata como falta de confianza y se deriva al menu.
    const intencion = porId.get(clases[indice]) || null;
    if (!intencion) {
      return { estado: "sin_confianza", intencion: null, confianza };
    }

    return {
      estado: confianza >= UMBRAL_CONFIANZA ? "respuesta" : "sin_confianza",
      intencion,
      confianza,
    };
  }

  // ---- Navegacion del catalogo (no usa el modelo) ----

  function categorias() {
    return catalogo.categorias;
  }

  function subtemas(idCategoria) {
    const vistos = [];
    for (const i of catalogo.intenciones) {
      if (i.categoria === idCategoria && !vistos.includes(i.subtema)) {
        vistos.push(i.subtema);
      }
    }
    return vistos;
  }

  function preguntas(idCategoria, subtema) {
    return catalogo.intenciones.filter(
      (i) => i.categoria === idCategoria && i.subtema === subtema
    );
  }

  function porIdIntencion(id) {
    return porId.get(id) || null;
  }

  return {
    iniciar,
    cargarModelo,
    modeloDisponible,
    clasificar,
    categorias,
    subtemas,
    preguntas,
    porIdIntencion,
    UMBRAL_CONFIANZA,
  };
})();
