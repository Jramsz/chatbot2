"""
Lectura del catalogo y construccion de lo que el navegador necesita mostrar.

Lo usan entrenar.py y actualizar_catalogo.py: que ambos produzcan EXACTAMENTE
el mismo catalogo.json evita que un cambio de contenido se vea distinto segun
el camino por el que se publico.
"""

import json
import re
import sys
from pathlib import Path

from validar import esta_activa, validar

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "contenido" / "intenciones.json"
SALIDA_WEB = RAIZ / "web" / "datos"
FUERA_DE_ALCANCE = RAIZ / "contenido" / "fuera-de-alcance.json"
MOTOR_JS = RAIZ / "web" / "motor.js"

# Clase extra del modelo para las consultas ajenas al catalogo. No es una
# intencion: no esta en catalogo.json, asi que el navegador la trata como
# "sin confianza" y deriva al menu. Su id esta reservado.
CLASE_FUERA = "fuera-de-alcance"


def leer_umbrales(ruta=MOTOR_JS):
    """UMBRAL_CONFIANZA y COBERTURA_MINIMA tal como los usa el navegador.

    Se leen de motor.js para que la medicion del entrenamiento use exactamente
    los mismos valores que el widget publicado: una sola fuente.
    """
    texto = Path(ruta).read_text(encoding="utf-8")
    valores = []
    for nombre in ("UMBRAL_CONFIANZA", "COBERTURA_MINIMA"):
        m = re.search(rf"^const {nombre} = ([0-9.]+);", texto, re.MULTILINE)
        if not m:
            raise ValueError(f"No se encontro 'const {nombre} = <numero>;' en {ruta}")
        valores.append(float(m.group(1)))
    return tuple(valores)


def cargar_catalogo(ruta=CATALOGO):
    """Lee y valida el catalogo. Si tiene errores, termina el proceso."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    errores, avisos = validar(datos, cargar_fuera_de_alcance())
    for a in avisos:
        print(f"AVISO: {a}")
    if errores:
        print(f"\nEl catalogo tiene {len(errores)} error(es):")
        for e in errores:
            print(f"  - {e}")
        sys.exit(1)
    return datos


def cargar_fuera_de_alcance(ruta=FUERA_DE_ALCANCE):
    """Consultas que el asistente no debe responder. Lista vacia si no hay archivo."""
    ruta = Path(ruta)
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8")).get("consultas", [])


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
