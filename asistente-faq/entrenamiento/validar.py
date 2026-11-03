"""
Valida el catalogo de intenciones antes de entrenar.

Se ejecuta ANTES del entrenamiento. Si encuentra errores, detiene el proceso:
un catalogo invalido produce un modelo defectuoso o rompe el asistente.

Uso:
    python entrenamiento/validar.py

Codigo de salida 0 si el catalogo es valido, 1 si tiene errores.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from preprocesamiento import normalizar

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "contenido" / "intenciones.json"

# Una intencion con patrones necesita al menos este numero para que el modelo
# la aprenda. Una intencion SIN patrones es valida: queda solo en el menu.
PATRONES_MINIMOS = 4


def esta_activa(intencion):
    """Una intencion con "activa": false esta retirada: no aparece en el menu
    ni se entrena, pero su id sigue reservado y no puede reutilizarse."""
    return intencion.get("activa", True) is not False


def validar(datos):
    errores = []
    avisos = []

    categorias = {c["id"] for c in datos.get("categorias", [])}
    if not categorias:
        errores.append("No hay categorias definidas.")

    intenciones = datos.get("intenciones", [])
    if not intenciones:
        errores.append("No hay intenciones definidas.")
        return errores, avisos

    # Identificadores duplicados (tambien entre retiradas: el id esta reservado)
    for id_, veces in Counter(i.get("id") for i in intenciones).items():
        if veces > 1:
            errores.append(f"Identificador duplicado: '{id_}' aparece {veces} veces.")

    if not any(esta_activa(i) for i in intenciones):
        errores.append("Todas las intenciones estan retiradas (activa: false).")

    # Patrones que aparecen en mas de una intencion: el modelo recibe
    # senales contradictorias y aprende mal ambas.
    ubicacion = {}
    for intencion in intenciones:
        if not esta_activa(intencion):
            continue
        for patron in intencion.get("patrones", []):
            clave = " ".join(normalizar(patron))
            if not clave:
                avisos.append(
                    f"[{intencion.get('id')}] el patron '{patron}' queda vacio "
                    "tras normalizar: no aporta nada al entrenamiento."
                )
                continue
            if clave in ubicacion and ubicacion[clave] != intencion.get("id"):
                errores.append(
                    f"El patron '{patron}' colisiona con la intencion "
                    f"'{ubicacion[clave]}' tras normalizar."
                )
            ubicacion[clave] = intencion.get("id")

    for intencion in intenciones:
        id_ = intencion.get("id", "(sin id)")

        for campo in ("id", "categoria", "pregunta", "respuesta"):
            if not str(intencion.get(campo, "")).strip():
                errores.append(f"[{id_}] campo obligatorio vacio: '{campo}'.")

        if "activa" in intencion and not isinstance(intencion["activa"], bool):
            errores.append(f"[{id_}] 'activa' debe ser true o false.")

        # Invariante 3: una sola respuesta por intencion, nunca una lista.
        if not isinstance(intencion.get("respuesta", ""), str):
            errores.append(f"[{id_}] 'respuesta' debe ser un texto, no una lista.")

        if intencion.get("categoria") not in categorias:
            errores.append(
                f"[{id_}] categoria inexistente: '{intencion.get('categoria')}'."
            )

        if not esta_activa(intencion):
            continue

        patrones = intencion.get("patrones", [])
        if not patrones:
            avisos.append(
                f"[{id_}] no tiene patrones: aparece en el menu pero el "
                "modelo no la reconoce al escribirla."
            )
        elif len(patrones) < PATRONES_MINIMOS:
            errores.append(
                f"[{id_}] tiene {len(patrones)} patrones; agregue al menos "
                f"{PATRONES_MINIMOS} o dejela sin patrones."
            )

        if len(set(patrones)) != len(patrones):
            avisos.append(f"[{id_}] tiene patrones repetidos entre si.")

    return errores, avisos


def main():
    if not CATALOGO.exists():
        print(f"No se encontro el catalogo en {CATALOGO}")
        return 1

    datos = json.loads(CATALOGO.read_text(encoding="utf-8"))
    errores, avisos = validar(datos)

    n_int = len(datos.get("intenciones", []))
    n_pat = sum(len(i.get("patrones", [])) for i in datos.get("intenciones", []))
    print(f"Intenciones: {n_int}   Patrones: {n_pat}")

    for a in avisos:
        print(f"AVISO: {a}")

    if errores:
        print(f"\n{len(errores)} error(es):")
        for e in errores:
            print(f"  - {e}")
        print("\nNo entrenar hasta corregir.")
        return 1

    print("Catalogo valido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
