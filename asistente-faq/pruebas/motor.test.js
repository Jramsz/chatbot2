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
async function cargarMotor({ probabilidades, clases = ["vigente", "otra"], modelo = true }) {
  const datos = {
    "datos/catalogo.json": CATALOGO,
    "datos/vocabulario.json": ["nota", "boleta"],
    "datos/clases.json": clases,
  };
  const tf = {
    loadLayersModel: async () => {
      if (!modelo) throw new Error("modelo no disponible");
      return { predict: () => ({ dataSync: () => probabilidades }) };
    },
    tidy: (f) => f(),
    tensor2d: (x) => x,
  };
  const contexto = {
    tf,
    console: { ...console, warn() {} },
    fetch: async (ruta) => ({ ok: true, json: async () => datos[ruta] }),
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
