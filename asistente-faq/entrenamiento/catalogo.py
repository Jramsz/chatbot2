"""
Lectura del catalogo y construccion de lo que el navegador necesita mostrar.

Lo usan entrenar.py y actualizar_catalogo.py: que ambos produzcan EXACTAMENTE
el mismo catalogo.json evita que un cambio de contenido se vea distinto segun
el camino por el que se publico.
"""

import json
import sys
from pathlib import Path

from validar import esta_activa, validar

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "contenido" / "intenciones.json"
SALIDA_WEB = RAIZ / "web" / "datos"


def cargar_catalogo(ruta=CATALOGO):
    """Lee y valida el catalogo. Si tiene errores, termina el proceso."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    errores, avisos = validar(datos)
    for a in avisos:
        print(f"AVISO: {a}")
    if errores:
        print(f"\nEl catalogo tiene {len(errores)} error(es):")
        for e in errores:
            print(f"  - {e}")
        sys.exit(1)
    return datos


def catalogo_para_web(datos):
    """Catalogo reducido a lo que el navegador necesita: sin los patrones.

    Las intenciones retiradas (activa: false) no se publican, y tampoco las
    categorias que quedan sin ninguna intencion activa: un menu con una
    categoria vacia deja al estudiante sin salida.
    """
    activas = [i for i in datos["intenciones"] if esta_activa(i)]
    usadas = {i["categoria"] for i in activas}
    return {
        "version": datos.get("version"),
        "categorias": [c for c in datos["categorias"] if c["id"] in usadas],
        "intenciones": [
            {
                "id": i["id"],
                "categoria": i["categoria"],
                "subtema": i.get("subtema", ""),
                "pregunta": i["pregunta"],
                "respuesta": i["respuesta"],
            }
            for i in activas
        ],
    }


def escribir_json(ruta, contenido):
    Path(ruta).write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")
