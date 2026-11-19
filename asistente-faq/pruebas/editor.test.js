// Pruebas del editor que no necesitan navegador: codificacion del contenido
// que viaja a GitHub y llamadas a la API con fetch simulado.
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const GitHub = require(path.join(__dirname, "..", "editor", "github.js"));

test("el contenido con tildes y eñes sobrevive la ida y vuelta en base64", () => {
  const texto = '{"pregunta": "¿Qué hago si perdí el carné? Ñandú, acción"}\n';
  assert.equal(GitHub.deBase64(GitHub.aBase64(texto)), texto);
});

test("GitHub entrega el base64 partido en lineas y se lee igual", () => {
  const b64 = GitHub.aBase64("línea única con acentos: áéíóú");
  const partido = b64.match(/.{1,10}/g).join("\n");
  assert.equal(GitHub.deBase64(partido), "línea única con acentos: áéíóú");
});

function conFetch(respuestas, fn) {
  const original = global.fetch;
  const llamadas = [];
  global.fetch = async (url, opciones) => {
    llamadas.push({ url, opciones });
    const [estado, cuerpo] = respuestas.shift();
    return { ok: estado < 400, status: estado, json: async () => cuerpo };
  };
  return fn(llamadas).finally(() => { global.fetch = original; });
}

test("un token sin permiso de escritura se detecta", () =>
  conFetch([[200, { login: "ana" }], [200, { permissions: { push: false } }]], async () => {
    const r = await GitHub.comprobarAcceso("t", "o/r");
    assert.deepEqual(r, { usuario: "ana", puedeEscribir: false });
  }));

test("un token invalido da un mensaje claro", () =>
  conFetch([[401, {}], [401, {}]], async () => {
    await assert.rejects(GitHub.comprobarAcceso("t", "o/r"), (e) => e.estado === 401 && /venció/.test(e.message));
  }));

test("guardar envia la version leida y el contenido en base64, solo a api.github.com", () =>
  conFetch([[200, { content: { sha: "nuevo" }, commit: { sha: "c1", html_url: "u" } }]], async (llamadas) => {
    const r = await GitHub.guardarArchivo("t", "o/r", "main", "a/b.json", "ñ", "viejo", "msg");
    assert.deepEqual(r, { sha: "nuevo", commit: "u", commitSha: "c1" });
    const { url, opciones } = llamadas[0];
    assert.ok(url.startsWith("https://api.github.com/repos/o/r/contents/a/b.json"));
    const cuerpo = JSON.parse(opciones.body);
    assert.equal(cuerpo.sha, "viejo");
    assert.equal(cuerpo.branch, "main");
    assert.equal(GitHub.deBase64(cuerpo.content), "ñ");
    assert.equal(opciones.headers.Authorization, "Bearer t");
  }));

test("si otra persona guardo antes, el conflicto se informa", () =>
  conFetch([[409, {}]], async () => {
    await assert.rejects(GitHub.guardarArchivo("t", "o/r", "main", "x", "y", "s", "m"),
      (e) => e.estado === 409 && /Recargue/.test(e.message));
  }));

test("sin permiso para ver Actions, el estado de la publicacion se omite", () =>
  conFetch([[403, {}]], async () => {
    assert.equal(await GitHub.ultimaPublicacion("t", "o/r", "main"), null);
  }));
