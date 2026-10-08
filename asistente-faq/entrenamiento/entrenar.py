"""
Entrena el clasificador de intenciones y exporta todo lo que necesita el navegador.

Flujo:
    1. valida el catalogo (llama a validar.py)
    2. mide la exactitud con validacion cruzada (el vocabulario de cada
       pliegue se construye solo con sus patrones de entrenamiento)
    3. aplica el umbral de aceptacion sobre la exactitud media
    4. si lo supera, reentrena con TODOS los patrones
    5. guarda modelo Keras, vocabulario, clases y respuestas

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
PLIEGUES = 5              # validacion cruzada: cada patron se prueba una vez
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


def asignar_pliegues(datos):
    """Reparte los patrones de cada intencion en PLIEGUES grupos parejos.

    Devuelve las clases y una lista de (tokens, clase, pliegue). Repartir por
    intencion (y no al azar sobre el total) garantiza que cada intencion
    aparezca en casi todos los pliegues de prueba.

    Las intenciones sin patrones no son clases del modelo: solo viven en el
    menu. Asi el catalogo puede crecer sin reentrenar para cada pregunta.
    """
    azar = random.Random(SEMILLA)
    entrenables = [i for i in datos["intenciones"] if i.get("patrones")]
    clases = [i["id"] for i in entrenables]
    ejemplos = []
    for clase, intencion in enumerate(entrenables):
        patrones = list(intencion["patrones"])
        azar.shuffle(patrones)
        for n, patron in enumerate(patrones):
            ejemplos.append((normalizar(patron), clase, n % PLIEGUES))
    return clases, ejemplos


def construir_vocabulario(ejemplos):
    """Terminos ordenados de los ejemplos dados.

    Se construye SOLO con los ejemplos de entrenamiento: incluir los de
    prueba filtraria informacion y inflaria la exactitud medida.
    """
    return sorted({t for tokens, _, _ in ejemplos for t in tokens})


def vectorizar(ejemplos, vocabulario, n_clases):
    posicion = {t: n for n, t in enumerate(vocabulario)}
    X = np.zeros((len(ejemplos), len(vocabulario)), dtype="float32")
    y = np.zeros((len(ejemplos), n_clases), dtype="float32")
    for fila, (tokens, clase, _) in enumerate(ejemplos):
        for t in tokens:
            if t in posicion:
                X[fila, posicion[t]] = 1.0
        y[fila, clase] = 1.0
    return X, y


def entrenar_modelo(X, y, semilla):
    import tensorflow as tf

    # Misma semilla, mismo modelo: sin esto la exactitud cambia entre corridas
    # y no se puede saber si un cambio en el catalogo mejoro o empeoro algo.
    tf.keras.utils.set_random_seed(semilla)
    modelo = construir_modelo(X.shape[1], y.shape[1])
    modelo.fit(X, y, epochs=EPOCAS, batch_size=LOTE, verbose=0)
    return modelo


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


def validacion_cruzada(clases, ejemplos):
    """Exactitud por pliegue y aciertos acumulados por intencion."""
    exactitudes = []
    aciertos = [0] * len(clases)
    totales = [0] * len(clases)
    huerfanos = 0

    for k in range(PLIEGUES):
        entrenamiento = [e for e in ejemplos if e[2] != k]
        prueba = [e for e in ejemplos if e[2] == k]
        vocabulario = construir_vocabulario(entrenamiento)
        X_ent, y_ent = vectorizar(entrenamiento, vocabulario, len(clases))
        X_pru, y_pru = vectorizar(prueba, vocabulario, len(clases))

        # Un patron de prueba sin ningun termino conocido es imposible de
        # clasificar; se cuenta aparte para saber cuanto pesa en la medida.
        huerfanos += int((X_pru.sum(axis=1) == 0).sum())

        modelo = entrenar_modelo(X_ent, y_ent, SEMILLA + k)
        pred = np.argmax(modelo.predict(X_pru, verbose=0), axis=1)
        real = np.argmax(y_pru, axis=1)
        exactitudes.append(float((pred == real).mean()))
        for r, p in zip(real, pred):
            totales[r] += 1
            aciertos[r] += int(r == p)
        print(f"  pliegue {k + 1}/{PLIEGUES}: {exactitudes[-1]:.3f}")

    por_intencion = [
        (aciertos[c] / totales[c], clases[c]) for c in range(len(clases)) if totales[c]
    ]
    return exactitudes, sorted(por_intencion), huerfanos


def main():
    datos = cargar_catalogo()
    clases, ejemplos = asignar_pliegues(datos)
    print(f"Intenciones: {len(clases)}   Patrones: {len(ejemplos)}")
    print(f"Validacion cruzada de {PLIEGUES} pliegues:")

    exactitudes, por_intencion, huerfanos = validacion_cruzada(clases, ejemplos)
    media = float(np.mean(exactitudes))
    print(f"\nExactitud: {media:.3f} +/- {float(np.std(exactitudes)):.3f} "
          f"(minimo {min(exactitudes):.3f}, maximo {max(exactitudes):.3f})")
    if huerfanos:
        print(f"AVISO: {huerfanos} patron(es) de prueba no compartian ningun "
              "termino con el vocabulario de entrenamiento.")
    print("Intenciones con peor acierto (agregar mas patrones):")
    for acierto, clase in por_intencion[:3]:
        print(f"  - {clase}: {acierto:.2f}")

    if media < EXACTITUD_MINIMA:
        print(
            f"\nLa exactitud esta por debajo del umbral de {EXACTITUD_MINIMA:.2f}. "
            "No se publica; se conserva la version anterior."
        )
        return 1

    # El modelo publicado se entrena con TODOS los patrones: los pliegues solo
    # sirven para medir. Descartar patrones en el modelo final desperdicia datos.
    vocabulario = construir_vocabulario(ejemplos)
    X, y = vectorizar(ejemplos, vocabulario, len(clases))
    print(f"\nEntrenando el modelo final: {len(vocabulario)} terminos, "
          f"{len(ejemplos)} patrones.")
    modelo = entrenar_modelo(X, y, SEMILLA)

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
