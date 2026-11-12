"""
Verifica que preprocesamiento.py y web/preprocesamiento.js produzcan
EXACTAMENTE los mismos tokens para el mismo texto.

Esta verificacion es obligatoria antes de publicar. Una divergencia entre
ambas implementaciones hace que el modelo clasifique mal sin emitir ningun
error visible: es un fallo silencioso.

Compara los casos escritos a mano de CASOS y, ademas, TODOS los textos del
contenido: patrones del catalogo, consultas fuera de alcance y consultas de
aceptacion. Son exactamente los textos con los que se entrena y se mide el
modelo, asi que una divergencia en cualquiera de ellos se detecta aqui.

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
CONTENIDO = RAIZ / "contenido"

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
    "mi ni\u006e\u0303o perdi\u0301 la boleta",  # ñ y í descompuestas (NFD)
]


def textos_del_contenido():
    """Todos los textos que el modelo ve: patrones (incluidas las intenciones
    retiradas), consultas fuera de alcance y consultas de aceptacion."""
    def leer(nombre):
        ruta = CONTENIDO / nombre
        return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}

    textos = [p for i in leer("intenciones.json").get("intenciones", [])
              for p in i.get("patrones", [])]
    textos += leer("fuera-de-alcance.json").get("consultas", [])
    textos += [c["consulta"] for c in leer("consultas-de-aceptacion.json").get("consultas", [])]
    return textos


def tokens_js(casos):
    """Ejecuta la version JavaScript sobre los mismos casos.

    Los casos van por la entrada estandar y no en la linea de comandos: en
    Windows esta se limita a ~32 000 caracteres y el contenido la supera."""
    script = (
        f"const {{ normalizar }} = require({json.dumps(str(JS))});"
        "let entrada = '';"
        "process.stdin.setEncoding('utf8');"
        "process.stdin.on('data', (d) => { entrada += d; });"
        "process.stdin.on('end', () => {"
        "  process.stdout.write(JSON.stringify(JSON.parse(entrada).map(normalizar)));"
        "});"
    )
    resultado = subprocess.run(
        ["node", "-e", script], input=json.dumps(casos, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return json.loads(resultado.stdout)


def main():
    corpus = textos_del_contenido()
    casos = list(dict.fromkeys(CASOS + corpus))   # sin repetidos, en orden
    esperado = [normalizar(c) for c in casos]
    obtenido = tokens_js(casos)

    fallos = []
    for caso, py, js in zip(casos, esperado, obtenido):
        if py != js:
            fallos.append((caso, py, js))

    print(f"Casos verificados: {len(casos)} ({len(CASOS)} escritos a mano y "
          f"{len(casos) - len(CASOS)} del contenido)")

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
