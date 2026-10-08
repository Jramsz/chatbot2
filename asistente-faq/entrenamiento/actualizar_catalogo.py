"""
Actualiza SOLO el catalogo del navegador (web/datos/catalogo.json), sin
reentrenar el modelo y sin necesitar TensorFlow.

Sirve para lo que no cambia lo que el modelo sabe reconocer:
    - corregir el texto de una respuesta o de una pregunta
    - agregar una pregunta al menu (sin patrones)
    - mover una pregunta de categoria o subtema

Lo que SI requiere reentrenar (entrenar.py): agregar o cambiar patrones.

Uso:
    python entrenamiento/actualizar_catalogo.py            # valida y escribe
    python entrenamiento/actualizar_catalogo.py --revisar  # solo muestra cambios

Codigo de salida 0 si todo esta bien, 1 si el catalogo tiene errores.
"""

import json
import sys

from catalogo import (
    CATALOGO,
    SALIDA_WEB,
    cargar_catalogo,
    catalogo_para_web,
    escribir_json,
)


def leer_json(ruta):
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def comparar(nuevo, anterior):
    """Ids agregados, retirados y con pregunta o respuesta distinta."""
    previas = {i["id"]: i for i in (anterior or {}).get("intenciones", [])}
    actuales = {i["id"]: i for i in nuevo["intenciones"]}
    agregadas = [i for i in actuales if i not in previas]
    retiradas = [i for i in previas if i not in actuales]
    cambiadas = [
        i for i in actuales
        if i in previas and any(
            actuales[i].get(c) != previas[i].get(c)
            for c in ("categoria", "subtema", "pregunta", "respuesta")
        )
    ]
    return agregadas, retiradas, cambiadas


def avisos_de_modelo(datos, clases_entrenadas):
    """Diferencias entre el catalogo y lo que el modelo publicado conoce."""
    if clases_entrenadas is None:
        return []
    ids = {i["id"] for i in datos["intenciones"]}
    con_patrones = {i["id"] for i in datos["intenciones"] if i.get("patrones")}
    avisos = []
    for c in clases_entrenadas:
        if c not in ids:
            avisos.append(
                f"El modelo aun conoce '{c}', que ya no esta en el catalogo: "
                "si alguien la escribe, el asistente lo deriva al menu hasta "
                "que se reentrene."
            )
    for i in sorted(con_patrones - set(clases_entrenadas)):
        avisos.append(
            f"'{i}' tiene patrones pero el modelo publicado no la conoce: "
            "aparece en el menu, y para reconocerla al escribir hay que "
            "reentrenar (entrenar.py)."
        )
    return avisos


def main(argv):
    solo_revisar = "--revisar" in argv
    datos = cargar_catalogo(CATALOGO)
    nuevo = catalogo_para_web(datos)

    anterior = leer_json(SALIDA_WEB / "catalogo.json")
    agregadas, retiradas, cambiadas = comparar(nuevo, anterior)

    if anterior is None:
        print("No hay catalogo publicado todavia: se creara uno nuevo.")
    for etiqueta, ids in (
        ("Agregadas", agregadas), ("Retiradas", retiradas), ("Modificadas", cambiadas)
    ):
        if ids:
            print(f"{etiqueta} ({len(ids)}): " + ", ".join(ids))
    if anterior is not None and not (agregadas or retiradas or cambiadas):
        print("Sin cambios en preguntas ni respuestas.")

    for aviso in avisos_de_modelo(datos, leer_json(SALIDA_WEB / "clases.json")):
        print(f"AVISO: {aviso}")

    if solo_revisar:
        print("\nSolo revision: no se escribio ningun archivo.")
        return 0

    SALIDA_WEB.mkdir(parents=True, exist_ok=True)
    escribir_json(SALIDA_WEB / "catalogo.json", nuevo)
    print(f"\nListo. Publicar unicamente: {SALIDA_WEB / 'catalogo.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
