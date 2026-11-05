"""Pruebas de la clase de fuera de alcance. Requieren numpy (entorno .venv)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "entrenamiento"))

import actualizar_catalogo as ac  # noqa: E402
from catalogo import CLASE_FUERA, cargar_fuera_de_alcance, leer_umbrales  # noqa: E402
from validar import validar  # noqa: E402

try:
    import entrenar  # noqa: E402  (importa numpy)
except ImportError:  # pragma: no cover
    entrenar = None

PATRONES = ["uno dos", "tres cuatro", "cinco seis", "siete ocho"]


def datos(*ids):
    return {
        "categorias": [{"id": "c", "nombre": "C"}],
        "intenciones": [
            {"id": i, "categoria": "c", "subtema": "s", "pregunta": "p",
             "respuesta": "r", "patrones": PATRONES}
            for i in ids
        ],
    }


class FueraDeAlcance(unittest.TestCase):
    def test_el_id_esta_reservado(self):
        errores, _ = validar(datos("a", CLASE_FUERA))
        self.assertTrue(any("reservado" in e for e in errores))

    def test_no_avisa_por_la_clase_reservada(self):
        self.assertEqual(ac.avisos_de_modelo(datos("a"), ["a", CLASE_FUERA]), [])

    def test_el_archivo_del_repositorio_tiene_consultas(self):
        self.assertGreaterEqual(len(cargar_fuera_de_alcance()), 30)

    @unittest.skipIf(entrenar is None, "requiere numpy")
    def test_las_ajenas_son_la_ultima_clase(self):
        clases, ejemplos = entrenar.asignar_pliegues(datos("a", "b"), ["hola", "chao"])
        self.assertEqual(clases, ["a", "b", CLASE_FUERA])
        self.assertEqual(sum(1 for e in ejemplos if e[1] == 2), 2)

    @unittest.skipIf(entrenar is None, "requiere numpy")
    def test_sin_ajenas_no_hay_clase_extra(self):
        clases, _ = entrenar.asignar_pliegues(datos("a", "b"))
        self.assertEqual(clases, ["a", "b"])


class Colisiones(unittest.TestCase):
    def test_consulta_ajena_igual_a_un_patron_es_error(self):
        errores, _ = validar(datos("a"), ["Tres CUATRO"])   # igual tras normalizar
        self.assertTrue(any("fuera de alcance" in e for e in errores))

    def test_consulta_ajena_distinta_no_es_error(self):
        errores, _ = validar(datos("a"), ["quien gano el partido"])
        self.assertEqual(errores, [])

    def test_el_repositorio_no_tiene_colisiones(self):
        import json
        raiz = Path(__file__).resolve().parent.parent
        catalogo = json.loads((raiz / "contenido" / "intenciones.json").read_text(encoding="utf-8"))
        errores, _ = validar(catalogo, cargar_fuera_de_alcance())
        self.assertEqual(errores, [])


class Umbrales(unittest.TestCase):
    def test_se_leen_de_motor_js(self):
        umbral, cobertura = leer_umbrales()
        self.assertTrue(0 < umbral <= 1)
        self.assertTrue(0 <= cobertura <= 1)

    def test_falla_si_motor_js_no_los_declara(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write("const OTRA = 1;")
        with self.assertRaises(ValueError):
            leer_umbrales(f.name)

    @unittest.skipIf(entrenar is None, "requiere numpy")
    def test_cobertura(self):
        self.assertEqual(entrenar.cobertura(["a", "b", "c", "d"], {"a", "b", "c"}), 0.75)
        self.assertEqual(entrenar.cobertura([], {"a"}), 0.0)


if __name__ == "__main__":
    unittest.main()
