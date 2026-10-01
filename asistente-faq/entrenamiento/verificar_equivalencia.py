"""
Verifica que preprocesamiento.py y web/preprocesamiento.js produzcan
EXACTAMENTE los mismos tokens para el mismo texto.

Esta verificacion es obligatoria antes de publicar. Una divergencia entre
ambas implementaciones hace que el modelo clasifique mal sin emitir ningun
error visible: es un fallo silencioso.

Requiere Node.js instalado.

Uso:
    python entrenamiento/verificar_equivalencia.py

Codigo de salida 0 si son equivalentes, 1 si divergen.
"""

import json
import subprocess
import sys
from pathlib import Path

from preprocesamiento import normalizar

RAIZ = Path(__file__).resolve().parent.parent
JS = RAIZ / "web" / "preprocesamiento.js"

# Casos que cubren: acentos, mayusculas, signos, enes, numeros, plurales,
# formas verbales, palabras vacias, escritura informal y cadenas limite.
CASOS = [
    "¿Qué hago si perdí la boleta de notas?",
    "Se me extravió el reporte de NOTAS",
    "como solicito una constancia de estudios",
    "Cuándo entregan los útiles escolares",
    "necesito informacion sobre becas de bachillerato",
    "quiero saber del año escolar 2026",
    "TRAMITE de traslado a otro centro educativo",
    "q hago si no encuentro mi carnet",
    "cuanto cuesta la certificacion???",
    "mi niño perdió el uniforme",
    "solicitud   con    espacios   multiples",
    "Matrícula, inscripción y matriculación",
    "¡¡¡AYUDA!!! no sé qué hacer",
    "el señor director dijo que sí",
    "",
    "   ",
    "a de la el",
    "ñ",
    "123 456",
    "reposicion de documentos academicos oficiales",
]


def tokens_js(casos):
    """Ejecuta la version JavaScript sobre los mismos casos."""
    script = f"""
const {{ normalizar }} = require({json.dumps(str(JS))});
const casos = {json.dumps(casos, ensure_ascii=False)};
process.stdout.write(JSON.stringify(casos.map(normalizar)));
"""
    resultado = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=True
    )
    return json.loads(resultado.stdout)


def main():
    esperado = [normalizar(c) for c in CASOS]
    obtenido = tokens_js(CASOS)

    fallos = []
    for caso, py, js in zip(CASOS, esperado, obtenido):
        if py != js:
            fallos.append((caso, py, js))

    print(f"Casos verificados: {len(CASOS)}")

    if not fallos:
        print("Las dos implementaciones son equivalentes.")
        return 0

    print(f"DIVERGENCIA en {len(fallos)} caso(s):\n")
    for caso, py, js in fallos:
        print(f"  entrada : {caso!r}")
        print(f"  python  : {py}")
        print(f"  javascript: {js}\n")
    print("No publicar hasta corregir.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
