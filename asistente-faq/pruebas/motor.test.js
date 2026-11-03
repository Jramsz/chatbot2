// Pruebas del motor sin navegador: se carga motor.js en un contexto aislado
// con un modelo y un fetch simulados. Cubren las invariantes 4 y 5 (el menu
// no depende del modelo; por debajo del umbral no se responde).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const WEB = path.join(__dirname, "..", "web");

const CATALOGO = {
  categorias: [{ id: "c", nombre: "Categoria" }],
  intenciones: [
    { id: "vigente", categoria: "c", subtema: "s", pregunta: "p", respuesta: "r" },
  ],
};

// `clases` es lo que el modelo conoce; puede incluir ids que ya no estan en
// el catalogo. `probabilidades` es la salida simulada del modelo.
// `entradasModelo` y `salidasModelo` son las dimensiones del modelo simulado;
// por defecto coinciden con el vocabulario (2) y las clases.
async function cargarMotor({
  probabilidades,
  clases = ["vigente", "otra"],
  modelo = true,
  entradasModelo = 2,
  salidasModelo = clases.length,
  llamadas = { fetch: [], modelo: [] },
}) {
  const datos = {
    "datos/catalogo.json": CATALOGO,
    "datos/vocabulario.json": ["nota", "boleta"],
    "datos/clases.json": clases,
  };
  const tf = {
    loadLayersModel: async (ruta, opciones) => {
      llamadas.modelo.push(opciones);
      if (!modelo) throw new Error("modelo no disponible");
      return {
        inputs: [{ shape: [null, entradasModelo] }],
        outputs: [{ shape: [null, salidasModelo] }],
        predict: () => ({ dataSync: () => probabilidades }),
      };
    },
    tidy: (f) => f(),
    tensor2d: (x) => x,
  };
  const contexto = {
    tf,
    console: { ...console, warn() {} },
    fetch: async (ruta, opciones) => {
      llamadas.fetch.push(opciones);
      return { ok: true, json: async () => datos[ruta] };
    },
  };
  vm.createContext(contexto);
  for (const archivo of ["preprocesamiento.js", "motor.js"]) {
    vm.runInContext(fs.readFileSync(path.join(WEB, archivo), "utf8"), contexto);
  }
  vm.runInContext("this.Motor = Motor;", contexto);
  await contexto.Motor.iniciar();
  await contexto.Motor.cargarModelo();
  return contexto.Motor;
}

test("responde cuando la confianza supera el umbral", async () => {
  const motor = await cargarMotor({ probabilidades: [0.95, 0.05] });
  const r = motor.clasificar("nota boleta");
  assert.equal(r.estado, "respuesta");
  assert.equal(r.intencion.id, "vigente");
});

test("no responde por debajo del umbral", async () => {
  const motor = await cargarMotor({ probabilidades: [0.6, 0.4] });
  const r = motor.clasificar("nota boleta");
  assert.equal(r.estado, "sin_confianza");
});

test("una intencion retirada del catalogo deriva al menu, sin intencion nula como respuesta", async () => {
  // El modelo viejo aun predice "retirada" con mucha confianza.
  const motor = await cargarMotor({
    clases: ["vigente", "retirada"],
    probabilidades: [0.05, 0.95],
  });
  const r = motor.clasificar("nota boleta");
  assert.equal(r.estado, "sin_confianza");
  assert.equal(r.intencion, null);
});

test("consulta sin terminos del vocabulario", async () => {
  const motor = await cargarMotor({ probabilidades: [0.95, 0.05] });
  assert.equal(motor.clasificar("zzz qqq").estado, "sin_terminos");
});

test("si el modelo falla, el menu sigue funcionando", async () => {
  const motor = await cargarMotor({ probabilidades: [], modelo: false });
  assert.equal(motor.modeloDisponible(), false);
  assert.equal(motor.clasificar("nota boleta").estado, "sin_modelo");
  assert.equal(motor.categorias().length, 1);
  assert.equal(motor.preguntas("c", "s").length, 1);
});

test("si el modelo no coincide con vocabulario y clases, opera solo con el menu", async () => {
  // Vocabulario de 2 terminos pero modelo de 5 entradas: se subieron por separado.
  const motor = await cargarMotor({ probabilidades: [0.95, 0.05], entradasModelo: 5 });
  assert.equal(motor.modeloDisponible(), false);
  assert.equal(motor.clasificar("nota boleta").estado, "sin_modelo");
  assert.equal(motor.preguntas("c", "s").length, 1);
});

test("si las clases no coinciden con las salidas del modelo, opera solo con el menu", async () => {
  const motor = await cargarMotor({ probabilidades: [0.95, 0.05], salidasModelo: 7 });
  assert.equal(motor.modeloDisponible(), false);
});

test("los archivos de datos y el modelo se piden con revalidacion", async () => {
  const llamadas = { fetch: [], modelo: [] };
  await cargarMotor({ probabilidades: [0.95, 0.05], llamadas });
  assert.equal(llamadas.fetch.length, 3);
  for (const opciones of llamadas.fetch) assert.equal(opciones.cache, "no-cache");
  assert.equal(llamadas.modelo[0].requestInit.cache, "no-cache");
});

test("con poca cobertura de vocabulario no responde aunque la confianza sea alta", async () => {
  // "nota partido ayer futbol": solo "nota" esta en el vocabulario (1 de 4).
  const motor = await cargarMotor({ probabilidades: [0.99, 0.01] });
  const r = motor.clasificar("nota partido ayer futbol");
  assert.equal(r.estado, "sin_confianza");
  assert.equal(r.intencion, null);
});

test("con cobertura suficiente responde aunque haya palabras desconocidas", async () => {
  // "nota boleta partido": 2 de 3 terminos conocidos, sobre la cobertura minima.
  const motor = await cargarMotor({ probabilidades: [0.99, 0.01] });
  assert.equal(motor.clasificar("nota boleta partido").estado, "respuesta");
});

test("la clase fuera-de-alcance deriva al menu", async () => {
  const motor = await cargarMotor({
    clases: ["vigente", "fuera-de-alcance"],
    probabilidades: [0.01, 0.99],
  });
  const r = motor.clasificar("nota boleta");
  assert.equal(r.estado, "sin_confianza");
  assert.equal(r.intencion, null);
});
