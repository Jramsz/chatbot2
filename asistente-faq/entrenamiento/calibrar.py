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
    python entrenamiento/calibrar.py                     # como entrenar.py
    python entrenamiento/calibrar.py --sin-clase-fuera   # para comparar

No escribe ningun archivo. Tarda lo mismo que la validacion cruzada.
"""

import sys

import numpy as np

from catalogo import CLASE_FUERA, cargar_catalogo, cargar_fuera_de_alcance
from catalogo import leer_umbrales
from entrenar import (
    PLIEGUES,
    SEMILLA,
    asignar_pliegues,
    construir_vocabulario,
    cobertura,
    entrenar_modelo,
    vectorizar,
)
from preprocesamiento import normalizar

UMBRALES = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99]
COBERTURAS = [0.0, 0.5, 0.6, 0.75]


def recolectar(clases, ejemplos, ajenas_aparte):
    """Predicciones fuera de pliegue: (confianza, acierto, cobertura) para el
    catalogo y (confianza, cobertura) para las consultas ajenas.

    Si el modelo tiene la clase de fuera de alcance, las consultas ajenas ya
    estan en `ejemplos` y cada una se evalua con el modelo que no la vio;
    predecir esa clase equivale a derivar al menu. Si no (`ajenas_aparte`),
    se evaluan contra todos los modelos sin haber entrenado con ellas.
    """
    dentro, fuera = [], []
    FUERA = clases.index(CLASE_FUERA) if CLASE_FUERA in clases else -1

    for k in range(PLIEGUES):
        entrenamiento = [e for e in ejemplos if e[2] != k]
        prueba = [e for e in ejemplos if e[2] == k]
        prueba += [(normalizar(q), FUERA, k) for q in ajenas_aparte]
        vocabulario = construir_vocabulario(entrenamiento)
        X, y = vectorizar(entrenamiento, vocabulario, len(clases))
        modelo = entrenar_modelo(X, y, SEMILLA + k)

        X_pru = vectorizar([(t, 0, 0) for t, _, _ in prueba], vocabulario, len(clases))[0]
        prob = modelo.predict(X_pru, verbose=0)
        for fila, (tokens, clase, _) in enumerate(prueba):
            pred = int(np.argmax(prob[fila]))
            derivada = X_pru[fila].sum() == 0 or pred == FUERA
            conf = 0.0 if derivada else float(prob[fila][pred])
            cob = 0.0 if derivada else cobertura(tokens, set(vocabulario))
            if clase == FUERA:
                fuera.append((conf, cob))
            else:
                dentro.append((conf, pred == clase, cob))
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
    consultas = cargar_fuera_de_alcance()
    sin_clase = "--sin-clase-fuera" in sys.argv
    if sin_clase:
        clases, ejemplos = asignar_pliegues(datos)
        ajenas_aparte = consultas
    else:
        clases, ejemplos = asignar_pliegues(datos, consultas)
        ajenas_aparte = []
    print(f"Fuera de alcance: {len(consultas)} consultas. " + (
        "Modelo SIN clase de fuera de alcance (comparacion)." if sin_clase
        else "Modelo con clase de fuera de alcance (como entrenar.py)."))
    dentro, fuera = recolectar(clases, ejemplos, ajenas_aparte)
    tabla(dentro, fuera)
    umbral, minima = leer_umbrales()
    print(f"\nValores actuales en web/motor.js: umbral {umbral}, cobertura {minima}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
