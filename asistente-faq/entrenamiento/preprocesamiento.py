"""
Normalizacion de texto en espanol para el asistente de preguntas frecuentes.

IMPORTANTE
----------
Este modulo tiene una copia gemela en web/preprocesamiento.js que debe producir
EXACTAMENTE la misma salida para la misma entrada. Si divergen, el modelo
clasifica mal sin emitir ningun error.

Cualquier cambio aqui debe replicarse alli, y debe verificarse ejecutando:

    python entrenamiento/verificar_equivalencia.py

No se usa NLTK ni ninguna libreria de procesamiento de lenguaje. La razon es
deliberada: los lematizadores y stemmers de biblioteca no tienen equivalente
exacto en JavaScript, y reimplementarlos introduce el riesgo de divergencia.
Las reglas de abajo son simples, deterministas y portables por construccion.
"""

# Vocales acentuadas y caracteres propios del espanol.
# Se translitera para que "perdi" y "perdí" produzcan el mismo token.
ACENTOS = {
    "á": "a", "à": "a", "ä": "a", "â": "a",
    "é": "e", "è": "e", "ë": "e", "ê": "e",
    "í": "i", "ì": "i", "ï": "i", "î": "i",
    "ó": "o", "ò": "o", "ö": "o", "ô": "o",
    "ú": "u", "ù": "u", "ü": "u", "û": "u",
    "ñ": "n", "ç": "c",
}

# Palabras sin valor discriminante. Lista corta y explicita: una lista larga
# elimina senal util en consultas breves como "que hago si perdi la boleta".
VACIAS = {
    "a", "al", "algo", "algun", "alguna", "algunas", "alguno", "algunos",
    "ante", "aqui", "como", "con", "cual", "cuales", "cuando", "de", "del",
    "desde", "donde", "dos", "el", "ella", "ellas", "ellos", "en", "entre",
    "era", "es", "esa", "esas", "ese", "eso", "esos", "esta", "estan",
    "estas", "este", "esto", "estos", "hay", "la", "las", "le", "les", "lo",
    "los", "mas", "me", "mi", "mis", "muy", "nos", "o", "otra", "otras",
    "otro", "otros", "para", "pero", "por", "porque", "que", "quien", "se",
    "segun", "ser", "si", "sin", "sobre", "son", "su", "sus", "tambien",
    "te", "tu", "tus", "un", "una", "unas", "uno", "unos", "y", "ya", "yo",
}

# Sufijos a recortar, ordenados de mas largo a mas corto.
# Se aplica el PRIMER sufijo que coincida y que deje una raiz de 4 caracteres
# o mas. No busca correccion linguistica, sino que formas de la misma familia
# ("solicito", "solicitar", "solicitud") converjan al mismo token.
SUFIJOS = [
    "amientos", "imientos", "amiento", "imiento",
    "aciones", "iciones", "ivamente", "abilidad",
    "adores", "adoras", "ancias", "encias", "idades",
    "acion", "icion", "ador", "adora", "ancia", "encia", "idad",
    "mente", "ables", "ibles", "able", "ible",
    "anzas", "anza", "istas", "ista",
    "icos", "icas", "ico", "ica",
    "osos", "osas", "oso", "osa",
    "ivos", "ivas", "ivo", "iva",
    "iendo", "ando",
    "ieron", "aron", "eron",
    "abas", "aban", "aba",
    "ados", "adas", "idos", "idas", "ado", "ada", "ido", "ida",
    "aria", "arias", "eria", "erias",
    "ar", "er", "ir",
    "es", "s",
]

RAIZ_MINIMA = 4
TOKEN_MINIMO = 3


def quitar_acentos(texto):
    return "".join(ACENTOS.get(c, c) for c in texto)


def solo_alfanumerico(texto):
    """Sustituye por espacio todo lo que no sea letra basica o digito."""
    salida = []
    for c in texto:
        if ("a" <= c <= "z") or ("0" <= c <= "9"):
            salida.append(c)
        else:
            salida.append(" ")
    return "".join(salida)


def recortar_sufijo(palabra):
    for sufijo in SUFIJOS:
        if palabra.endswith(sufijo) and len(palabra) - len(sufijo) >= RAIZ_MINIMA:
            return palabra[: -len(sufijo)]
    return palabra


def normalizar(texto):
    """Convierte una frase en su lista ordenada de tokens.

    Pasos, en este orden exacto:
      1. minusculas
      2. transliteracion de acentos y enes
      3. eliminacion de todo caracter no alfanumerico
      4. division por espacios
      5. descarte de palabras vacias
      6. descarte de tokens de menos de TOKEN_MINIMO caracteres
      7. recorte de sufijo
    """
    texto = texto.lower()
    texto = quitar_acentos(texto)
    texto = solo_alfanumerico(texto)

    tokens = []
    for palabra in texto.split():
        if palabra in VACIAS:
            continue
        if len(palabra) < TOKEN_MINIMO:
            continue
        tokens.append(recortar_sufijo(palabra))
    return tokens


def bolsa_de_palabras(texto, vocabulario):
    """Vector binario de presencia segun el vocabulario dado.

    vocabulario es una lista ordenada; el indice de cada termino en esa lista
    es su posicion en el vector. El orden debe ser identico al usado en el
    entrenamiento, por eso se guarda en vocabulario.json.
    """
    presentes = set(normalizar(texto))
    return [1 if termino in presentes else 0 for termino in vocabulario]


if __name__ == "__main__":
    ejemplos = [
        "¿Qué hago si perdí la boleta de notas?",
        "Se me extravió el reporte de NOTAS",
        "como solicito una constancia de estudios",
    ]
    for e in ejemplos:
        print(f"{e!r}\n  -> {normalizar(e)}")
