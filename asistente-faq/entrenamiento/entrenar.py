"""
Entrena el clasificador de intenciones y exporta todo lo que necesita el navegador.

Flujo:
    1. valida el catalogo (llama a validar.py)
    2. mide la exactitud con validacion cruzada (el vocabulario de cada
       pliegue se construye solo con sus patrones de entrenamiento)
    3. aplica las condiciones de publicacion (EXACTITUD_MINIMA, AJENAS_MAXIMA)
    4. si lo supera, reentrena con TODOS los patrones
    5. guarda modelo Keras, vocabulario, clases y respuestas

Uso:
    python entrenamiento/entrenar.py

Normalmente no se ejecuta solo: publicar.py lo llama y despues convierte el
modelo para el navegador y arma el entregable.

Codigo de salida 0 si el modelo alcanza el umbral, 1 si no.
"""

import os
import random
import sys
from collections import Counter

import numpy as np

from catalogo import (
    CLASE_FUERA,
    RAIZ,
    SALIDA_WEB,
    cargar_aceptacion,
    cargar_catalogo,
    cargar_fuera_de_alcance,
    catalogo_para_web,
    escribir_json,
    leer_umbrales,
)
from preprocesamiento import normalizar
from validar import esta_activa

SALIDA_MODELO = RAIZ / "modelo"

# El modelo se guarda en formato Keras 2: TensorFlow.js no puede leer el .h5 de
# Keras 3 (pesos con otro nombre y capa de entrada con otra clave). Debe
# fijarse ANTES de que se importe tensorflow.
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

SEMILLA = 42
PLIEGUES = 5              # validacion cruzada: cada patron se prueba una vez
EPOCAS = 300
LOTE = 8
# Condiciones para publicar un modelo, medidas con validacion cruzada.
# PROVISIONALES: fijadas sobre el catalogo generico de muestra; revisarlas con
# el supervisor con la primera medicion del contenido real.
EXACTITUD_MINIMA = 0.75   # aciertos sobre los patrones del catalogo
AJENAS_MAXIMA = 0.15      # consultas fuera de alcance que recibirian respuesta


def asignar_pliegues(datos, ajenas=()):
    """Reparte los patrones de cada intencion en PLIEGUES grupos parejos.

    Devuelve las clases y una lista de (tokens, clase, pliegue). Repartir por
    intencion (y no al azar sobre el total) garantiza que cada intencion
    aparezca en casi todos los pliegues de prueba.

    Las intenciones sin patrones o retiradas no son clases del modelo: solo
    viven en el menu (o en ninguna parte, si estan retiradas). Asi el catalogo puede crecer sin reentrenar para cada pregunta.
    """
    azar = random.Random(SEMILLA)
    entrenables = [
        i for i in datos["intenciones"] if esta_activa(i) and i.get("patrones")
    ]
    clases = [i["id"] for i in entrenables]
    ejemplos = []
    for clase, intencion in enumerate(entrenables):
        patrones = list(intencion["patrones"])
        azar.shuffle(patrones)
        for n, patron in enumerate(patrones):
            ejemplos.append((normalizar(patron), clase, n % PLIEGUES))

    # Las consultas ajenas forman una clase mas, la ultima. Sin ella, una
    # consulta que comparte una sola palabra con el catalogo ("quien gano el
    # partido") recibe confianza alta, porque el modelo solo conoce intenciones.
    if ajenas:
        clases.append(CLASE_FUERA)
        for n, consulta in enumerate(ajenas):
            ejemplos.append((normalizar(consulta), len(clases) - 1, n % PLIEGUES))
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


def cobertura(tokens, conocidos):
    """Fraccion de los terminos de la consulta que el modelo conoce.
    Gemela de la regla de COBERTURA_MINIMA en web/motor.js."""
    if not tokens:
        return 0.0
    return sum(t in conocidos for t in tokens) / len(tokens)


def decision_navegador(prob, tokens, conocidos, clases, umbral, cobertura_minima):
    """Lo que haria web/motor.js con esta consulta: el id de la intencion que
    responderia, o "menu" si deriva. Gemela de Motor.clasificar; si cambian
    las reglas alli, deben cambiar aqui.

    `prob` son las probabilidades del modelo para la consulta.
    """
    if not any(t in conocidos for t in tokens):
        return "menu"                              # sin terminos conocidos
    if cobertura(tokens, conocidos) < cobertura_minima:
        return "menu"
    p = int(np.argmax(prob))
    if clases[p] == CLASE_FUERA or prob[p] < umbral:
        return "menu"
    return clases[p]


def validacion_cruzada(clases, ejemplos):
    """Mide el modelo con validacion cruzada.

    Ademas de la exactitud (argmax sobre los patrones del catalogo) simula la
    decision del navegador con UMBRAL_CONFIANZA y COBERTURA_MINIMA de motor.js,
    para saber cuantas consultas ajenas recibirian respuesta.
    """
    umbral, cobertura_minima = leer_umbrales()
    fuera = clases.index(CLASE_FUERA) if CLASE_FUERA in clases else -1
    exactitudes = []
    aciertos = [0] * len(clases)
    totales = [0] * len(clases)
    confusiones = Counter()
    huerfanos = ajenas_total = ajenas_respondidas = catalogo_mal = catalogo_total = 0

    for k in range(PLIEGUES):
        entrenamiento = [e for e in ejemplos if e[2] != k]
        prueba = [e for e in ejemplos if e[2] == k]
        vocabulario = construir_vocabulario(entrenamiento)
        conocidos = set(vocabulario)
        X_ent, y_ent = vectorizar(entrenamiento, vocabulario, len(clases))
        X_pru, y_pru = vectorizar(prueba, vocabulario, len(clases))

        modelo = entrenar_modelo(X_ent, y_ent, SEMILLA + k)
        prob = modelo.predict(X_pru, verbose=0)
        pred = np.argmax(prob, axis=1)
        real = np.argmax(y_pru, axis=1)

        # La exactitud se mide solo sobre el catalogo; las consultas ajenas
        # se miden aparte, con las reglas del navegador.
        catalogo = real != fuera
        exactitudes.append(float((pred[catalogo] == real[catalogo]).mean()))

        for fila, (tokens, _, _) in enumerate(prueba):
            r, p = int(real[fila]), int(pred[fila])
            responde = decision_navegador(
                prob[fila], tokens, conocidos, clases, umbral, cobertura_minima
            ) != "menu"
            if r == fuera:
                ajenas_total += 1
                ajenas_respondidas += int(responde)
                continue
            # Un patron del catalogo sin ningun termino conocido es imposible
            # de clasificar; se cuenta aparte para saber cuanto pesa.
            huerfanos += int(X_pru[fila].sum() == 0)
            totales[r] += 1
            aciertos[r] += int(r == p)
            catalogo_total += 1
            catalogo_mal += int(responde and r != p)
            if r != p:
                confusiones[(clases[r], "menu" if p == fuera else clases[p])] += 1
        print(f"  pliegue {k + 1}/{PLIEGUES}: {exactitudes[-1]:.3f}")

    return {
        "exactitudes": exactitudes,
        "por_intencion": sorted(
            (aciertos[c] / totales[c], clases[c])
            for c in range(len(clases)) if totales[c] and c != fuera
        ),
        "confusiones": confusiones.most_common(5),
        "huerfanos": huerfanos,
        "tasa_ajenas": ajenas_respondidas / ajenas_total if ajenas_total else None,
        "tasa_mal": catalogo_mal / catalogo_total if catalogo_total else 0.0,
        "umbral": umbral,
        "cobertura_minima": cobertura_minima,
    }


def prueba_de_aceptacion(modelo, vocabulario, clases, casos):
    """Pasa cada consulta por el modelo con las reglas del navegador.

    Responder la intencion esperada es correcto; derivar al menu una consulta
    del catalogo es seguro (se informa); responder cualquier otra intencion,
    o responder algo a una consulta que esperaba "menu", es error.
    Devuelve el numero de errores.
    """
    umbral, cobertura_minima = leer_umbrales()
    conocidos = set(vocabulario)
    tokens = [normalizar(c["consulta"]) for c in casos]
    X, _ = vectorizar([(t, 0, 0) for t in tokens], vocabulario, len(clases))
    prob = modelo.predict(X, verbose=0)

    bien, al_menu, errores = 0, [], []
    for fila, caso in enumerate(casos):
        decision = decision_navegador(
            prob[fila], tokens[fila], conocidos, clases, umbral, cobertura_minima
        )
        if decision == caso["esperado"]:
            bien += 1
        elif decision == "menu":
            al_menu.append(caso)
        else:
            errores.append((caso, decision))

    print(f"\nPruebas de aceptacion: {bien}/{len(casos)} correctas, "
          f"{len(al_menu)} derivadas al menu, {len(errores)} respuestas equivocadas.")
    for caso in al_menu:
        print(f"  menu   '{caso['consulta']}' (esperaba {caso['esperado']})")
    for caso, decision in errores:
        print(f"  ERROR  '{caso['consulta']}' respondio {decision} "
              f"(esperaba {caso['esperado']})")
    return len(errores)


def validar_aceptacion(casos, clases):
    """Cada caso debe esperar "menu" o una intencion que el modelo conoce."""
    validos = set(clases) - {CLASE_FUERA} | {"menu"}
    malos = [c for c in casos if c.get("esperado") not in validos]
    for c in malos:
        print(f"Caso de aceptacion invalido: '{c.get('consulta')}' espera "
              f"'{c.get('esperado')}', que no es una intencion entrenada ni 'menu'.")
    return not malos


def main():
    datos = cargar_catalogo()
    ajenas = cargar_fuera_de_alcance()
    clases, ejemplos = asignar_pliegues(datos, ajenas)
    casos_aceptacion = cargar_aceptacion()
    if not validar_aceptacion(casos_aceptacion, clases):
        return 1
    print(f"Intenciones: {len(clases) - (1 if ajenas else 0)}   "
          f"Patrones: {len(ejemplos) - len(ajenas)}   Fuera de alcance: {len(ajenas)}")
    print(f"Validacion cruzada de {PLIEGUES} pliegues:")

    m = validacion_cruzada(clases, ejemplos)
    exactitudes = m["exactitudes"]
    media = float(np.mean(exactitudes))
    print(f"\nExactitud: {media:.3f} +/- {float(np.std(exactitudes)):.3f} "
          f"(minimo {min(exactitudes):.3f}, maximo {max(exactitudes):.3f})")
    if m["huerfanos"]:
        print(f"AVISO: {m['huerfanos']} patron(es) de prueba no compartian ningun "
              "termino con el vocabulario de entrenamiento.")
    print(f"Con umbral {m['umbral']} y cobertura {m['cobertura_minima']} (motor.js):")
    print(f"  consultas del catalogo respondidas con otra intencion: {m['tasa_mal']:.1%}")
    if m["tasa_ajenas"] is not None:
        print(f"  consultas fuera de alcance que recibirian respuesta: {m['tasa_ajenas']:.1%}")
    else:
        print("  AVISO: no hay contenido/fuera-de-alcance.json; no se puede medir.")
    print("Intenciones con peor acierto (agregar mas patrones):")
    for acierto, clase in m["por_intencion"][:3]:
        print(f"  - {clase}: {acierto:.2f}")
    if m["confusiones"]:
        print("Confusiones mas frecuentes (real -> predicha):")
        for (real, pred), veces in m["confusiones"]:
            print(f"  - {real} -> {pred}: {veces}")

    rechazos = []
    if media < EXACTITUD_MINIMA:
        rechazos.append(f"la exactitud ({media:.3f}) esta por debajo de {EXACTITUD_MINIMA:.2f}")
    if m["tasa_ajenas"] is not None and m["tasa_ajenas"] > AJENAS_MAXIMA:
        rechazos.append(
            f"responderia {m['tasa_ajenas']:.1%} de las consultas fuera de alcance "
            f"(maximo {AJENAS_MAXIMA:.0%})"
        )
    if rechazos:
        print("\nNo se publica; se conserva la version anterior:")
        for r in rechazos:
            print(f"  - {r}")
        return 1

    # El modelo publicado se entrena con TODOS los patrones: los pliegues solo
    # sirven para medir. Descartar patrones en el modelo final desperdicia datos.
    vocabulario = construir_vocabulario(ejemplos)
    X, y = vectorizar(ejemplos, vocabulario, len(clases))
    print(f"\nEntrenando el modelo final: {len(vocabulario)} terminos, "
          f"{len(ejemplos)} patrones.")
    modelo = entrenar_modelo(X, y, SEMILLA)

    # Pruebas de aceptacion sobre el modelo que se va a publicar (no sobre los
    # de los pliegues): es el que ve el estudiante, y entrenado en otra maquina
    # puede decidir distinto en consultas concretas aunque cumpla las metricas.
    if casos_aceptacion:
        errores = prueba_de_aceptacion(modelo, vocabulario, clases, casos_aceptacion)
        if errores:
            print("\nNo se publica: el modelo respondio mal consultas de "
                  "contenido/consultas-de-aceptacion.json (ver arriba).")
            return 1

    # ---- Exportacion ----
    SALIDA_MODELO.mkdir(exist_ok=True)
    SALIDA_WEB.mkdir(parents=True, exist_ok=True)

    modelo.save(SALIDA_MODELO / "modelo.h5")

    # El orden del vocabulario y de las clases es parte del contrato con el
    # navegador: si cambia sin reentrenar, las predicciones se desalinean.
    escribir_json(SALIDA_WEB / "vocabulario.json", vocabulario)
    escribir_json(SALIDA_WEB / "clases.json", clases)

    escribir_json(SALIDA_WEB / "catalogo.json", catalogo_para_web(datos))

    print(f"\nModelo guardado en {SALIDA_MODELO / 'modelo.h5'}")
    print(f"Datos para el navegador en {SALIDA_WEB}")
    print("Para convertirlo y armar el entregable: python entrenamiento/publicar.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
