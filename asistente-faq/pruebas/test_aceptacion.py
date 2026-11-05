"""Pruebas de la decision del navegador en Python y de las pruebas de
aceptacion. Requieren numpy (entorno .venv)."""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "entrenamiento"))

from catalogo import CLASE_FUERA, cargar_aceptacion  # noqa: E402

try:
    import numpy as np  # noqa: E402
    import entrenar  # noqa: E402
except ImportError:  # pragma: no cover
    entrenar = None

CLASES = ["a", "b", CLASE_FUERA]
CONOCIDOS = {"nota", "boleta", "beca"}


@unittest.skipIf(entrenar is None, "requiere numpy")
class DecisionNavegador(unittest.TestCase):
    def decidir(self, prob, tokens, umbral=0.9, cobertura=0.6):
        return entrenar.decision_navegador(
            np.array(prob), tokens, CONOCIDOS, CLASES, umbral, cobertura)

    def test_responde_sobre_el_umbral(self):
        self.assertEqual(self.decidir([0.95, 0.04, 0.01], ["nota", "boleta"]), "a")

    def test_bajo_el_umbral_va_al_menu(self):
        self.assertEqual(self.decidir([0.85, 0.14, 0.01], ["nota"]), "menu")

    def test_sin_terminos_conocidos_va_al_menu(self):
        self.assertEqual(self.decidir([0.99, 0.0, 0.01], ["pizza"]), "menu")

    def test_poca_cobertura_va_al_menu(self):
        self.assertEqual(self.decidir([0.99, 0.0, 0.01], ["nota", "x", "y"]), "menu")

    def test_clase_fuera_de_alcance_va_al_menu(self):
        self.assertEqual(self.decidir([0.0, 0.01, 0.99], ["nota"]), "menu")


class Falso:
    """Modelo que devuelve probabilidades fijas segun el primer termino."""
    def __init__(self, por_termino, vocabulario):
        self.por_termino, self.vocabulario = por_termino, vocabulario

    def predict(self, X, verbose=0):
        filas = []
        for x in X:
            presentes = [t for t, v in zip(self.vocabulario, x) if v]
            filas.append(self.por_termino.get(presentes[0] if presentes else None,
                                              [0.34, 0.33, 0.33]))
        return np.array(filas)


@unittest.skipIf(entrenar is None, "requiere numpy")
class PruebaDeAceptacion(unittest.TestCase):
    VOCABULARIO = ["beca", "boleta", "nota"]

    def correr(self, casos, por_termino):
        modelo = Falso(por_termino, self.VOCABULARIO)
        return entrenar.prueba_de_aceptacion(modelo, self.VOCABULARIO, CLASES, casos)

    def test_respuesta_esperada_no_es_error(self):
        casos = [{"consulta": "nota", "esperado": "a"}]
        self.assertEqual(self.correr(casos, {"nota": [0.95, 0.04, 0.01]}), 0)

    def test_derivar_al_menu_no_es_error(self):
        casos = [{"consulta": "nota", "esperado": "a"}]
        self.assertEqual(self.correr(casos, {"nota": [0.6, 0.39, 0.01]}), 0)

    def test_responder_otra_intencion_es_error(self):
        casos = [{"consulta": "nota", "esperado": "a"}]
        self.assertEqual(self.correr(casos, {"nota": [0.04, 0.95, 0.01]}), 1)

    def test_responder_una_consulta_ajena_es_error(self):
        casos = [{"consulta": "beca", "esperado": "menu"}]
        self.assertEqual(self.correr(casos, {"beca": [0.95, 0.04, 0.01]}), 1)

    def test_casos_invalidos(self):
        self.assertTrue(entrenar.validar_aceptacion([{"consulta": "x", "esperado": "menu"}], CLASES))
        self.assertFalse(entrenar.validar_aceptacion([{"consulta": "x", "esperado": "zzz"}], CLASES))
        self.assertFalse(entrenar.validar_aceptacion(
            [{"consulta": "x", "esperado": CLASE_FUERA}], CLASES))


class ArchivoDelRepositorio(unittest.TestCase):
    def test_los_casos_esperan_intenciones_existentes(self):
        catalogo = json.loads((RAIZ / "contenido" / "intenciones.json").read_text(encoding="utf-8"))
        ids = {i["id"] for i in catalogo["intenciones"] if i.get("activa", True) is not False}
        casos = cargar_aceptacion()
        self.assertGreaterEqual(len(casos), 30)
        for c in casos:
            self.assertIn(c["esperado"], ids | {"menu"}, c["consulta"])


if __name__ == "__main__":
    unittest.main()
