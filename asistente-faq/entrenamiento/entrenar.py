"""
Entrena el clasificador de intenciones y exporta todo lo que necesita el navegador.

Flujo:
    1. valida el catalogo (llama a validar.py)
    2. construye vocabulario y matriz de bolsa de palabras
    3. separa un conjunto de prueba
    4. entrena la red
    5. evalua y aplica el umbral de aceptacion
    6. guarda modelo Keras, vocabulario, clases y respuestas

Uso:
    python entrenamiento/entrenar.py

Tras esto, convertir el modelo para el navegador:
    tensorflowjs_converter --input_format keras \\
        modelo/modelo.h5 web/modelo

Codigo de salida 0 si el modelo alcanza el umbral, 1 si no.
"""

import json
import random
import sys
from pathlib import Path

import numpy as np

from preprocesamiento import normalizar
from validar import validar

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "contenido" / "intenciones.json"
SALIDA_MODELO = RAIZ / "modelo"
SALIDA_WEB = RAIZ / "web" / "datos"

SEMILLA = 42
PROPORCION_PRUEBA = 0.2   # patrones reservados por intencion
EPOCAS = 300
LOTE = 8
EXACTITUD_MINIMA = 0.80   # acordar con el supervisor tras la linea base


def cargar_catalogo():
    datos = json.loads(CATALOGO.read_text(encoding="utf-8"))
    errores, avisos = validar(datos)
    for a in avisos:
        print(f"AVISO: {a}")
    if errores:
        print(f"\nEl catalogo tiene {len(errores)} error(es):")
        for e in errores:
            print(f"  - {e}")
        sys.exit(1)
    return datos


def construir_datos(datos):
    """Devuelve vocabulario, clases y los conjuntos de entrenamiento y prueba."""
    random.seed(SEMILLA)

    clases = [i["id"] for i in datos["intenciones"]]
    indice_clase = {c: n for n, c in enumerate(clases)}

    entrenamiento, prueba = [], []
    vocabulario = set()

    for intencion in datos["intenciones"]:
        patrones = list(intencion["patrones"])
        random.shuffle(patrones)

        # Al menos un patron reservado para prueba, y al menos dos para entrenar.
        n_prueba = max(1, int(round(len(patrones) * PROPORCION_PRUEBA)))
        n_prueba = min(n_prueba, max(0, len(patrones) - 2))

        for n, patron in enumerate(patrones):
            tokens = normalizar(patron)
            destino = prueba if n < n_prueba else entrenamiento
            destino.append((tokens, indice_clase[intencion["id"]]))
            # El vocabulario se construye SOLO con los patrones de
            # entrenamiento: incluir los de prueba filtraria informacion.
            if destino is entrenamiento:
                vocabulario.update(tokens)

    vocabulario = sorted(vocabulario)
    posicion = {t: n for n, t in enumerate(vocabulario)}

    def vectorizar(conjunto):
        X = np.zeros((len(conjunto), len(vocabulario)), dtype="float32")
        y = np.zeros((len(conjunto), len(clases)), dtype="float32")
        for fila, (tokens, clase) in enumerate(conjunto):
            for t in tokens:
                if t in posicion:
                    X[fila, posicion[t]] = 1.0
            y[fila, clase] = 1.0
        return X, y

    X_ent, y_ent = vectorizar(entrenamiento)
    X_pru, y_pru = vectorizar(prueba)
    return vocabulario, clases, (X_ent, y_ent), (X_pru, y_pru)


def construir_modelo(n_entrada, n_salida):
    from tensorflow import keras
    from tensorflow.keras import layers

    modelo = keras.Sequential([
        layers.Input(shape=(n_entrada,)),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.5),
        layers.Dense(64, activation="relu"),
        layers.Dropout(0.5),
        layers.Dense(n_salida, activation="softmax"),
    ])
    modelo.compile(
        loss="categorical_crossentropy",
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        metrics=["accuracy"],
    )
    return modelo


def informe_por_intencion(modelo, X, y, clases):
    """Lista las intenciones que el modelo nunca acierta en el conjunto dado."""
    if len(X) == 0:
        return []
    predicciones = modelo.predict(X, verbose=0)
    aciertos, totales = {}, {}
    for fila in range(len(X)):
        real = clases[int(np.argmax(y[fila]))]
        pred = clases[int(np.argmax(predicciones[fila]))]
        totales[real] = totales.get(real, 0) + 1
        if real == pred:
            aciertos[real] = aciertos.get(real, 0) + 1
    return [c for c in totales if aciertos.get(c, 0) == 0]


def main():
    datos = cargar_catalogo()
    vocabulario, clases, (X_ent, y_ent), (X_pru, y_pru) = construir_datos(datos)

    print(f"Vocabulario: {len(vocabulario)} terminos")
    print(f"Intenciones: {len(clases)}")
    print(f"Entrenamiento: {len(X_ent)} patrones   Prueba: {len(X_pru)} patrones")

    # Un patron de prueba cuyos tokens no aparecen en el vocabulario es
    # imposible de clasificar: su vector es todo ceros. No es un error, pero
    # baja la exactitud medida y conviene saberlo.
    huerfanos = int((X_pru.sum(axis=1) == 0).sum()) if len(X_pru) else 0
    if huerfanos:
        print(
            f"AVISO: {huerfanos} patron(es) de prueba no comparten ningun "
            "termino con el vocabulario de entrenamiento. Son inclasificables "
            "por construccion; conviene ampliar los patrones de esas intenciones."
        )

    modelo = construir_modelo(len(vocabulario), len(clases))
    modelo.fit(X_ent, y_ent, epochs=EPOCAS, batch_size=LOTE, verbose=0)

    _, exactitud = modelo.evaluate(X_pru, y_pru, verbose=0)
    print(f"\nExactitud sobre el conjunto de prueba: {exactitud:.3f}")

    sin_acierto = informe_por_intencion(modelo, X_pru, y_pru, clases)
    if sin_acierto:
        print(f"Intenciones sin ningun acierto ({len(sin_acierto)}):")
        for c in sin_acierto:
            print(f"  - {c}  (agregar mas patrones)")

    if exactitud < EXACTITUD_MINIMA:
        print(
            f"\nLa exactitud esta por debajo del umbral de {EXACTITUD_MINIMA:.2f}. "
            "No se publica; se conserva la version anterior."
        )
        return 1

    # ---- Exportacion ----
    SALIDA_MODELO.mkdir(exist_ok=True)
    SALIDA_WEB.mkdir(parents=True, exist_ok=True)

    modelo.save(SALIDA_MODELO / "modelo.h5")

    # El orden del vocabulario y de las clases es parte del contrato con el
    # navegador: si cambia sin reentrenar, las predicciones se desalinean.
    (SALIDA_WEB / "vocabulario.json").write_text(
        json.dumps(vocabulario, ensure_ascii=False), encoding="utf-8"
    )
    (SALIDA_WEB / "clases.json").write_text(
        json.dumps(clases, ensure_ascii=False), encoding="utf-8"
    )

    # Catalogo reducido a lo que el navegador necesita mostrar.
    catalogo_web = {
        "version": datos.get("version"),
        "categorias": datos["categorias"],
        "intenciones": [
            {
                "id": i["id"],
                "categoria": i["categoria"],
                "subtema": i.get("subtema", ""),
                "pregunta": i["pregunta"],
                "respuesta": i["respuesta"],
            }
            for i in datos["intenciones"]
        ],
    }
    (SALIDA_WEB / "catalogo.json").write_text(
        json.dumps(catalogo_web, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nModelo guardado en {SALIDA_MODELO / 'modelo.h5'}")
    print(f"Datos para el navegador en {SALIDA_WEB}")
    print("\nSiguiente paso:")
    print("  tensorflowjs_converter --input_format keras "
          f"{SALIDA_MODELO / 'modelo.h5'} {RAIZ / 'web' / 'modelo'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
