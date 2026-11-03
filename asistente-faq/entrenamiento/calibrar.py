"""
Mide como se comporta el umbral de confianza antes de fijarlo.

Para cada pliegue de la validacion cruzada entrena un modelo y registra:
  - las consultas del catalogo que no vio (patrones del pliegue de prueba)
  - las consultas fuera de alcance (contenido/fuera-de-alcance.json)

Con eso calcula, para cada combinacion de umbral de confianza y cobertura
minima de vocabulario, cuanto responde bien, cuanto responde mal y cuantas
consultas ajenas responde (error grave: informa mal).

Cobertura = fraccion de los terminos de la consulta que el modelo conoce. Una
consulta como "quien gano el partido de ayer" comparte un solo termino
("gano") con el catalogo; el modelo igual puede dar confianza alta, porque
con bolsa de palabras ese unico termino decide todo.

Uso:
    python entrenamiento/calibrar.py                 # modelo actual
    python entrenamiento/calibrar.py --clase-fuera   # con clase "fuera de alcance"

No escribe ningun archivo. Tarda lo mismo que la validacion cruzada.
"""

import json
import sys

import numpy as np

from catalogo import RAIZ, cargar_catalogo
from entrenar import (
    PLIEGUES,
    SEMILLA,
    asignar_pliegues,
    construir_vocabulario,
    entrenar_modelo,
    vectorizar,
)
from preprocesamiento import normalizar

FUERA_DE_ALCANCE = RAIZ / "contenido" / "fuera-de-alcance.json"

UMBRALES = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99]
COBERTURAS = [0.0, 0.5, 0.6, 0.75]


def cobertura(tokens, vocabulario):
    if not tokens:
        return 0.0
    conocidos = set(vocabulario)
    return sum(t in conocidos for t in tokens) / len(tokens)


def recolectar(clases, ejemplos, consultas_fuera, clase_fuera):
    """Predicciones fuera de pliegue: (confianza, acierto, cobertura) para el
    catalogo y (confianza, cobertura) para las consultas ajenas.

    Con clase_fuera, las consultas ajenas de los otros pliegues se agregan al
    entrenamiento como una clase mas; predecir esa clase equivale a derivar al
    menu. Cada consulta ajena se evalua solo con el modelo que no la vio.
    """
    dentro, fuera = [], []
    n_clases = len(clases) + (1 if clase_fuera else 0)
    FUERA = len(clases)
    ajenas = [(normalizar(q), FUERA, n % PLIEGUES) for n, q in enumerate(consultas_fuera)]

    for k in range(PLIEGUES):
        entrenamiento = [e for e in ejemplos if e[2] != k]
        if clase_fuera:
            entrenamiento += [e for e in ajenas if e[2] != k]
            evaluar_ajenas = [e for e in ajenas if e[2] == k]
        else:
            evaluar_ajenas = ajenas
        prueba = [e for e in ejemplos if e[2] == k]
        vocabulario = construir_vocabulario(entrenamiento)
        X, y = vectorizar(entrenamiento, vocabulario, n_clases)
        modelo = entrenar_modelo(X, y, SEMILLA + k)

        X_pru, _ = vectorizar(prueba, vocabulario, n_clases)
        prob = modelo.predict(X_pru, verbose=0)
        for fila, (tokens, clase, _) in enumerate(prueba):
            pred = int(np.argmax(prob[fila]))
            if X_pru[fila].sum() == 0 or (clase_fuera and pred == FUERA):
                dentro.append((0.0, False, 0.0))   # va al menu
                continue
            dentro.append((float(prob[fila][pred]), pred == clase,
                           cobertura(tokens, vocabulario)))

        X_f, _ = vectorizar(evaluar_ajenas, vocabulario, n_clases)
        prob_f = modelo.predict(X_f, verbose=0)
        for fila, (tokens, _, _) in enumerate(evaluar_ajenas):
            pred = int(np.argmax(prob_f[fila]))
            if X_f[fila].sum() == 0 or (clase_fuera and pred == FUERA):
                fuera.append((0.0, 0.0))
                continue
            fuera.append((float(prob_f[fila][pred]), cobertura(tokens, vocabulario)))
        print(f"  pliegue {k + 1}/{PLIEGUES} listo")

    return dentro, fuera


def tabla(dentro, fuera):
    print("\nResponde solo si confianza >= umbral Y cobertura >= minima.")
    print("  bien  = consultas del catalogo respondidas con la intencion correcta")
    print("  mal   = consultas del catalogo respondidas con una intencion equivocada")
    print("  ajena = consultas fuera de alcance que reciben respuesta (error grave)")
    for minima in COBERTURAS:
        print(f"\nCobertura minima {minima:.2f}")
        print("  umbral   bien    mal   ajena")
        for u in UMBRALES:
            bien = sum(c >= u and cob >= minima and ok for c, ok, cob in dentro)
            mal = sum(c >= u and cob >= minima and not ok for c, ok, cob in dentro)
            ajena = sum(c >= u and cob >= minima for c, cob in fuera)
            print(f"  {u:5.2f}  {bien / len(dentro):6.1%} {mal / len(dentro):6.1%} "
                  f"{ajena / len(fuera):6.1%}")


def main():
    datos = cargar_catalogo()
    consultas = json.loads(FUERA_DE_ALCANCE.read_text(encoding="utf-8"))["consultas"]
    clase_fuera = "--clase-fuera" in sys.argv
    clases, ejemplos = asignar_pliegues(datos)
    print(f"Catalogo: {len(ejemplos)} patrones. Fuera de alcance: {len(consultas)} "
          "consultas. " + ("Entrenando con clase de fuera de alcance."
                           if clase_fuera else "Sin clase de fuera de alcance."))
    dentro, fuera = recolectar(clases, ejemplos, consultas, clase_fuera)
    tabla(dentro, fuera)
    return 0


if __name__ == "__main__":
    sys.exit(main())
