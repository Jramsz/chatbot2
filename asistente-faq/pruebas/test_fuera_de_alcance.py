"""Pruebas de la clase de fuera de alcance. Requieren numpy (entorno .venv)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "entrenamiento"))

import actualizar_catalogo as ac  # noqa: E402
from catalogo import CLASE_FUERA, cargar_fuera_de_alcance  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
