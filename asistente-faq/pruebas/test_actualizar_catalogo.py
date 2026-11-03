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
from validar import validar  # noqa: E402


def intencion(id_, respuesta="r", patrones=None, subtema="s", categoria="c", **extra):
    return {
        "id": id_, "categoria": categoria, "subtema": subtema,
        "pregunta": f"pregunta {id_}", "respuesta": respuesta,
        "patrones": patrones or [], **extra,
    }


def datos(*intenciones):
    return {
        "version": "t",
        "categorias": [{"id": "c", "nombre": "C"}, {"id": "d", "nombre": "D"}],
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


class Retiradas(unittest.TestCase):
    def test_una_intencion_retirada_no_se_publica(self):
        web = catalogo.catalogo_para_web(
            datos(intencion("a"), intencion("b", activa=False))
        )
        self.assertEqual([i["id"] for i in web["intenciones"]], ["a"])

    def test_una_categoria_sin_intenciones_activas_no_se_publica(self):
        web = catalogo.catalogo_para_web(
            datos(intencion("a"), intencion("b", categoria="d", activa=False))
        )
        self.assertEqual([c["id"] for c in web["categorias"]], ["c"])

    def test_retirar_se_informa_como_retirada(self):
        anterior = catalogo.catalogo_para_web(datos(intencion("a"), intencion("b")))
        nuevo = catalogo.catalogo_para_web(datos(intencion("a"), intencion("b", activa=False)))
        self.assertEqual(ac.comparar(nuevo, anterior), ([], ["b"], []))

    def test_borrar_una_entrada_publicada_avisa(self):
        anterior = catalogo.catalogo_para_web(datos(intencion("a"), intencion("b")))
        self.assertEqual(ac.ids_borrados(datos(intencion("a")), anterior), ["b"])

    def test_retirar_con_activa_false_no_se_considera_borrado(self):
        anterior = catalogo.catalogo_para_web(datos(intencion("a"), intencion("b")))
        d = datos(intencion("a"), intencion("b", activa=False))
        self.assertEqual(ac.ids_borrados(d, anterior), [])

    def test_el_modelo_que_aun_conoce_una_retirada_avisa(self):
        d = datos(intencion("a"), intencion("b", activa=False))
        avisos = ac.avisos_de_modelo(d, ["a", "b"])
        self.assertEqual(len(avisos), 1)
        self.assertIn("'b'", avisos[0])


class Validacion(unittest.TestCase):
    PATRONES = ["uno dos", "tres cuatro", "cinco seis", "siete ocho"]

    def test_los_patrones_de_una_retirada_no_colisionan_ni_cuentan(self):
        d = datos(
            intencion("a", patrones=self.PATRONES),
            intencion("b", patrones=self.PATRONES[:2], activa=False),
        )
        errores, _ = validar(d)
        self.assertEqual(errores, [])

    def test_activa_debe_ser_booleano(self):
        errores, _ = validar(datos(intencion("a"), intencion("b", activa="no")))
        self.assertTrue(any("'activa'" in e for e in errores))

    def test_no_pueden_estar_todas_retiradas(self):
        errores, _ = validar(datos(intencion("a", activa=False)))
        self.assertTrue(any("retiradas" in e for e in errores))

    def test_el_id_de_una_retirada_sigue_reservado(self):
        errores, _ = validar(datos(intencion("a"), intencion("a", activa=False)))
        self.assertTrue(any("duplicado" in e for e in errores))

    def test_respuesta_no_puede_ser_lista(self):
        errores, _ = validar(datos(intencion("a", respuesta=["uno", "dos"])))
        self.assertTrue(any("'respuesta'" in e for e in errores))


if __name__ == "__main__":
    unittest.main()
