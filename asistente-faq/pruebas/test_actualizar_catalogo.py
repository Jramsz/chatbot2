"""Pruebas de actualizar_catalogo.py. Se ejecutan con:

    python -m unittest discover -s pruebas -p "test_*.py"
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "entrenamiento"))

import actualizar_catalogo as ac  # noqa: E402
import catalogo  # noqa: E402


def intencion(id_, respuesta="r", patrones=None, subtema="s"):
    return {
        "id": id_, "categoria": "c", "subtema": subtema, "pregunta": f"pregunta {id_}",
        "respuesta": respuesta, "patrones": patrones or [],
    }


def datos(*intenciones):
    return {
        "version": "t", "categorias": [{"id": "c", "nombre": "C"}],
        "intenciones": list(intenciones),
    }


class Comparar(unittest.TestCase):
    def test_detecta_agregadas_retiradas_y_cambiadas(self):
        anterior = catalogo.catalogo_para_web(datos(intencion("a"), intencion("b")))
        nuevo = catalogo.catalogo_para_web(
            datos(intencion("a", respuesta="distinta"), intencion("c"))
        )
        self.assertEqual(ac.comparar(nuevo, anterior), (["c"], ["b"], ["a"]))

    def test_sin_catalogo_previo_todo_es_nuevo(self):
        nuevo = catalogo.catalogo_para_web(datos(intencion("a")))
        self.assertEqual(ac.comparar(nuevo, None), (["a"], [], []))


class Avisos(unittest.TestCase):
    PATRONES = ["uno dos", "tres cuatro", "cinco seis", "siete ocho"]

    def test_clase_entrenada_que_ya_no_existe(self):
        d = datos(intencion("a"))
        avisos = ac.avisos_de_modelo(d, ["a", "vieja"])
        self.assertEqual(len(avisos), 1)
        self.assertIn("vieja", avisos[0])

    def test_intencion_con_patrones_que_el_modelo_no_conoce(self):
        d = datos(intencion("a", patrones=self.PATRONES))
        avisos = ac.avisos_de_modelo(d, [])
        self.assertEqual(len(avisos), 1)
        self.assertIn("reentrenar", avisos[0])

    def test_intencion_solo_de_menu_no_avisa(self):
        self.assertEqual(ac.avisos_de_modelo(datos(intencion("a")), []), [])

    def test_sin_modelo_publicado_no_avisa(self):
        self.assertEqual(ac.avisos_de_modelo(datos(intencion("a")), None), [])


class CatalogoParaWeb(unittest.TestCase):
    def test_no_expone_los_patrones(self):
        web = catalogo.catalogo_para_web(
            datos(intencion("a", patrones=Avisos.PATRONES))
        )
        self.assertNotIn("patrones", web["intenciones"][0])


class Escritura(unittest.TestCase):
    def test_escribe_solo_el_catalogo(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp)
            catalogo.escribir_json(
                salida / "catalogo.json", catalogo.catalogo_para_web(datos(intencion("a")))
            )
            self.assertEqual(
                [p.name for p in salida.iterdir()], ["catalogo.json"]
            )
            leido = json.loads((salida / "catalogo.json").read_text(encoding="utf-8"))
            self.assertEqual(leido["intenciones"][0]["id"], "a")


if __name__ == "__main__":
    unittest.main()
