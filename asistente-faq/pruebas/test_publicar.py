"""Pruebas del contrato modelo-datos en publicar.py y del corpus de la
verificacion de equivalencia. No requieren TensorFlow."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "entrenamiento"))

import publicar  # noqa: E402
import verificar_equivalencia  # noqa: E402


def escribir(ruta, contenido):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido), encoding="utf-8")


def model_json(entradas, salidas):
    return {
        "modelTopology": {"model_config": {"config": {"layers": [
            {"class_name": "InputLayer", "config": {"batch_input_shape": [None, entradas]}},
            {"class_name": "Dense", "config": {"units": 8}},
            {"class_name": "Dense", "config": {"units": salidas}},
        ]}}},
        "weightsManifest": [{"paths": ["pesos.bin"]}],
    }


class Contrato(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.origen, self.convertido, self.web = base / "modelo", base / "modelo" / "tfjs", base / "web"
        # generacion nueva: 3 terminos, 2 clases (orden b, a)
        escribir(self.origen / "vocabulario.json", ["x", "y", "z"])
        escribir(self.origen / "clases.json", ["b", "a"])
        escribir(self.convertido / "model.json", model_json(3, 2))
        (self.convertido / "pesos.bin").write_bytes(b"nuevo")
        # web/ con la generacion anterior: mismas dimensiones, otro orden
        escribir(self.web / "datos" / "vocabulario.json", ["x", "y", "z"])
        escribir(self.web / "datos" / "clases.json", ["a", "b"])
        escribir(self.web / "datos" / "catalogo.json", {"intenciones": []})
        escribir(self.web / "modelo" / "model.json", model_json(3, 2))
        (self.web / "modelo" / "pesos.bin").write_bytes(b"viejo")
        (self.web / "modelo" / "sobrante.bin").write_bytes(b"viejo")

    def tearDown(self):
        self.tmp.cleanup()

    def test_instala_modelo_y_datos_de_la_misma_generacion(self):
        publicar.instalar_modelo(self.origen, self.convertido, self.web)
        clases = json.loads((self.web / "datos" / "clases.json").read_text(encoding="utf-8"))
        self.assertEqual(clases, ["b", "a"])                 # el orden nuevo
        self.assertEqual((self.web / "modelo" / "pesos.bin").read_bytes(), b"nuevo")
        self.assertFalse((self.web / "modelo" / "sobrante.bin").exists())
        self.assertTrue((self.web / "datos" / "catalogo.json").exists())   # no lo toca
        publicar.comprobar_contrato(self.web)                 # no falla

    def test_detecta_dimensiones_distintas(self):
        escribir(self.web / "datos" / "clases.json", ["a", "b", "c"])
        with self.assertRaises(SystemExit):
            publicar.comprobar_contrato(self.web)

    def test_detecta_pesos_faltantes(self):
        (self.web / "modelo" / "pesos.bin").unlink()
        with self.assertRaises(SystemExit):
            publicar.comprobar_contrato(self.web)


class CorpusDeEquivalencia(unittest.TestCase):
    def test_incluye_todo_el_contenido(self):
        textos = verificar_equivalencia.textos_del_contenido()
        catalogo = json.loads((RAIZ / "contenido" / "intenciones.json").read_text(encoding="utf-8"))
        patrones = sum(len(i.get("patrones", [])) for i in catalogo["intenciones"])
        self.assertGreater(len(textos), patrones)            # patrones + ajenas + aceptacion
        self.assertIn("como saber mis notas", textos)        # viene de la aceptacion


if __name__ == "__main__":
    unittest.main()
