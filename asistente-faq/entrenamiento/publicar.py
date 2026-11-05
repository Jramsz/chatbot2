"""
Arma el entregable completo en un solo paso.

Pasos, en este orden; si uno falla, se detiene sin armar nada:
    1. valida el catalogo                      (validar.py)
    2. verifica Python contra JavaScript       (verificar_equivalencia.py)
    3. entrena y aplica las condiciones        (entrenar.py)
    4. convierte el modelo a TensorFlow.js     (tensorflowjs_converter)
    5. comprueba que modelo, vocabulario y clases coinciden
    6. copia todo en la carpeta de salida

Resultado (por defecto en entrega/):
    entrega/asistente/   El widget. Es lo que se entrega al ministerio.
    entrega/index.html   Pagina de demostracion con el widget embebido.

Uso:
    python entrenamiento/publicar.py
    python entrenamiento/publicar.py --sin-entrenar        # reusa modelo y datos ya generados
    python entrenamiento/publicar.py --conversor RUTA      # tensorflowjs_converter en otra ruta

Por defecto el conversor se busca en .venv-conversion (entorno aparte: ver
requirements.txt). Codigo de salida 0 si el entregable quedo armado.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRENAMIENTO = RAIZ / "entrenamiento"
WEB = RAIZ / "web"
DEMO = RAIZ / "demo"

CONVERSOR_POR_DEFECTO = (
    RAIZ / ".venv-conversion" / "Scripts" / "tensorflowjs_converter.exe"
    if os.name == "nt"
    else RAIZ / ".venv-conversion" / "bin" / "tensorflowjs_converter"
)


def paso(titulo, comando):
    print(f"\n== {titulo}")
    if subprocess.run(comando, cwd=RAIZ).returncode != 0:
        print(f"\nFallo: {titulo}. No se armo el entregable.")
        sys.exit(1)


def comprobar_contrato():
    """Invariante 6: el modelo convertido y los datos deben ser de la misma
    generacion. Se revisa aqui para que un entregable inconsistente nunca
    llegue a publicarse."""
    datos = WEB / "datos"
    modelo = json.loads((WEB / "modelo" / "model.json").read_text(encoding="utf-8"))
    vocabulario = json.loads((datos / "vocabulario.json").read_text(encoding="utf-8"))
    clases = json.loads((datos / "clases.json").read_text(encoding="utf-8"))

    capas = modelo["modelTopology"]["model_config"]["config"]["layers"]
    entrada = next(c for c in capas if c["class_name"] == "InputLayer")
    entradas = entrada["config"]["batch_input_shape"][1]
    salidas = [c for c in capas if c["class_name"] == "Dense"][-1]["config"]["units"]
    if entradas != len(vocabulario) or salidas != len(clases):
        print(f"\nEl modelo ({entradas} entradas, {salidas} salidas) no coincide con "
              f"vocabulario.json ({len(vocabulario)}) y clases.json ({len(clases)}).")
        sys.exit(1)
    for peso in modelo["weightsManifest"][0]["paths"]:
        if not (WEB / "modelo" / peso).exists():
            print(f"\nFalta el archivo de pesos web/modelo/{peso}.")
            sys.exit(1)
    print(f"Contrato correcto: {entradas} terminos, {salidas} clases.")


def main():
    args = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    args.add_argument("--sin-entrenar", action="store_true",
                      help="reusar web/datos y web/modelo ya generados")
    args.add_argument("--conversor", type=Path, default=CONVERSOR_POR_DEFECTO,
                      help="ruta de tensorflowjs_converter")
    args.add_argument("--salida", type=Path, default=RAIZ / "entrega")
    opciones = args.parse_args()

    python = sys.executable
    paso("Validar el catalogo", [python, str(ENTRENAMIENTO / "validar.py")])
    paso("Verificar Python contra JavaScript",
         [python, str(ENTRENAMIENTO / "verificar_equivalencia.py")])

    if not opciones.sin_entrenar:
        if not opciones.conversor.exists():
            print(f"\nNo se encontro el conversor en {opciones.conversor}.\n"
                  "Instalelo en un entorno aparte (ver requirements.txt) o use --conversor.")
            sys.exit(1)
        paso("Entrenar", [python, str(ENTRENAMIENTO / "entrenar.py")])
        shutil.rmtree(WEB / "modelo", ignore_errors=True)
        paso("Convertir a TensorFlow.js", [
            str(opciones.conversor), "--input_format", "keras",
            str(RAIZ / "modelo" / "modelo.h5"), str(WEB / "modelo"),
        ])

    print("\n== Comprobar modelo, vocabulario y clases")
    comprobar_contrato()

    print("\n== Armar el entregable")
    salida = opciones.salida
    shutil.rmtree(salida, ignore_errors=True)
    shutil.copytree(WEB, salida / "asistente")
    shutil.copy(DEMO / "index.html", salida / "index.html")
    total = sum(f.stat().st_size for f in (salida / "asistente").rglob("*") if f.is_file())
    print(f"Listo: {salida}")
    print(f"  asistente/   el widget, {total / 1e6:.1f} MB (lo que se entrega)")
    print("  index.html   pagina de demostracion con el widget embebido")
    print(f"\nProbar en local:  cd {salida} && python -m http.server 8000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
