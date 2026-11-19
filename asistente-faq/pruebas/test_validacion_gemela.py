"""El validador del editor (editor/validacion.js) debe coincidir con el de la
publicacion (entrenamiento/validar.py): si el editor deja guardar algo que la
publicacion rechaza, el administrador se entera tarde. Compara cuantos errores
y avisos da cada uno sobre los mismos catalogos. Requiere Node."""

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "entrenamiento"))

from validar import validar  # noqa: E402

PATRONES = ["boleta perdida hoy", "reponer libreta notas", "duplicado boleta", "extravio libreta"]
BASE = {
    "categorias": [{"id": "c", "nombre": "C"}],
    "intenciones": [
        {"id": "a", "categoria": "c", "subtema": "s", "prioridad": 1, "pregunta": "p",
         "respuesta": "r", "patrones": PATRONES},
        {"id": "b", "categoria": "c", "subtema": "s", "prioridad": 2, "pregunta": "p",
         "respuesta": "r", "patrones": ["beca estudio", "solicitar beca", "beca bachillerato", "ayuda economica"]},
    ],
}


def variante(cambio):
    datos = copy.deepcopy(BASE)
    cambio(datos)
    return datos


CASOS = {
    "valido": (BASE, []),
    "id duplicado": (variante(lambda d: d["intenciones"][1].update(id="a")), []),
    "id reservado": (variante(lambda d: d["intenciones"][1].update(id="fuera-de-alcance")), []),
    "todas retiradas": (variante(lambda d: [i.update(activa=False) for i in d["intenciones"]]), []),
    "patron repetido entre preguntas": (variante(lambda d: d["intenciones"][1]["patrones"].append("Boleta perdida, hoy")), []),
    "patron vacio": (variante(lambda d: d["intenciones"][0]["patrones"].append("de la el")), []),
    "colision con ajena": (BASE, ["boleta perdida hoy"]),
    "campos vacios": (variante(lambda d: d["intenciones"][0].update(pregunta=" ", respuesta="")), []),
    "prioridad invalida": (variante(lambda d: d["intenciones"][0].update(prioridad=0)), []),
    "activa no booleana": (variante(lambda d: d["intenciones"][0].update(activa="no")), []),
    "respuesta lista": (variante(lambda d: d["intenciones"][0].update(respuesta=["x", "y"])), []),
    "categoria inexistente": (variante(lambda d: d["intenciones"][0].update(categoria="zzz")), []),
    "sin patrones": (variante(lambda d: d["intenciones"][0].update(patrones=[])), []),
    "pocos patrones": (variante(lambda d: d["intenciones"][0].update(patrones=PATRONES[:2])), []),
    "pocos patrones pero retirada": (variante(lambda d: d["intenciones"][0].update(patrones=PATRONES[:2], activa=False)), []),
    "patrones repetidos": (variante(lambda d: d["intenciones"][0]["patrones"].append(PATRONES[0])), []),
}


# Casos que son validos (a lo sumo con avisos); el resto debe dar errores.
SIN_ERRORES = {"valido", "catalogo del repositorio", "sin patrones", "patron vacio",
               "patrones repetidos", "pocos patrones pero retirada"}


def validar_js(casos):
    script = (
        f"const {{ normalizar }} = require({json.dumps(str(RAIZ / 'web' / 'preprocesamiento.js'))});"
        f"const {{ validarCatalogo }} = require({json.dumps(str(RAIZ / 'editor' / 'validacion.js'))});"
        "let e = ''; process.stdin.on('data', (d) => { e += d; });"
        "process.stdin.on('end', () => {"
        "  const r = JSON.parse(e).map(([datos, ajenas]) => {"
        "    const v = validarCatalogo(datos, ajenas, normalizar);"
        "    return [v.errores.length, v.avisos.length];"
        "  });"
        "  process.stdout.write(JSON.stringify(r));"
        "});"
    )
    salida = subprocess.run(["node", "-e", script], input=json.dumps(casos, ensure_ascii=False),
                            capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(salida.stdout)


class ValidacionGemela(unittest.TestCase):
    def test_mismos_errores_y_avisos_que_validar_py(self):
        catalogo = json.loads((RAIZ / "contenido" / "intenciones.json").read_text(encoding="utf-8"))
        ajenas = json.loads((RAIZ / "contenido" / "fuera-de-alcance.json").read_text(encoding="utf-8"))["consultas"]
        casos = dict(CASOS, **{"catalogo del repositorio": (catalogo, ajenas)})
        js = validar_js(list(casos.values()))
        for (nombre, (datos, ajenas)), (errores_js, avisos_js) in zip(casos.items(), js):
            errores_py, avisos_py = validar(datos, ajenas)
            with self.subTest(caso=nombre):
                self.assertEqual((errores_js, avisos_js), (len(errores_py), len(avisos_py)))
            if nombre not in SIN_ERRORES:
                with self.subTest(caso=nombre, detalle="debe dar al menos un error"):
                    self.assertGreater(errores_js, 0)


if __name__ == "__main__":
    unittest.main()
