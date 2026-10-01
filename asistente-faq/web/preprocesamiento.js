/*
 * Normalizacion de texto en espanol para el asistente de preguntas frecuentes.
 *
 * IMPORTANTE
 * ----------
 * Este archivo es la copia gemela de entrenamiento/preprocesamiento.py y debe
 * producir EXACTAMENTE la misma salida para la misma entrada. Si divergen, el
 * modelo clasifica mal sin emitir ningun error.
 *
 * Cualquier cambio aqui debe replicarse alli, y debe verificarse ejecutando:
 *
 *     python entrenamiento/verificar_equivalencia.py
 */

const ACENTOS = {
  "á": "a", "à": "a", "ä": "a", "â": "a",
  "é": "e", "è": "e", "ë": "e", "ê": "e",
  "í": "i", "ì": "i", "ï": "i", "î": "i",
  "ó": "o", "ò": "o", "ö": "o", "ô": "o",
  "ú": "u", "ù": "u", "ü": "u", "û": "u",
  "ñ": "n", "ç": "c",
};

const VACIAS = new Set([
  "a", "al", "algo", "algun", "alguna", "algunas", "alguno", "algunos",
  "ante", "aqui", "como", "con", "cual", "cuales", "cuando", "de", "del",
  "desde", "donde", "dos", "el", "ella", "ellas", "ellos", "en", "entre",
  "era", "es", "esa", "esas", "ese", "eso", "esos", "esta", "estan",
  "estas", "este", "esto", "estos", "hay", "la", "las", "le", "les", "lo",
  "los", "mas", "me", "mi", "mis", "muy", "nos", "o", "otra", "otras",
  "otro", "otros", "para", "pero", "por", "porque", "que", "quien", "se",
  "segun", "ser", "si", "sin", "sobre", "son", "su", "sus", "tambien",
  "te", "tu", "tus", "un", "una", "unas", "uno", "unos", "y", "ya", "yo",
]);

const SUFIJOS = [
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
];

const RAIZ_MINIMA = 4;
const TOKEN_MINIMO = 3;

function quitarAcentos(texto) {
  let salida = "";
  for (const c of texto) {
    salida += ACENTOS[c] !== undefined ? ACENTOS[c] : c;
  }
  return salida;
}

function soloAlfanumerico(texto) {
  let salida = "";
  for (const c of texto) {
    if ((c >= "a" && c <= "z") || (c >= "0" && c <= "9")) {
      salida += c;
    } else {
      salida += " ";
    }
  }
  return salida;
}

function recortarSufijo(palabra) {
  for (const sufijo of SUFIJOS) {
    if (palabra.endsWith(sufijo) && palabra.length - sufijo.length >= RAIZ_MINIMA) {
      return palabra.slice(0, palabra.length - sufijo.length);
    }
  }
  return palabra;
}

/* Convierte una frase en su lista ordenada de tokens.
 * Pasos en el mismo orden exacto que la version Python. */
function normalizar(texto) {
  texto = texto.toLowerCase();
  texto = quitarAcentos(texto);
  texto = soloAlfanumerico(texto);

  const tokens = [];
  for (const palabra of texto.split(/\s+/)) {
    if (palabra === "") continue;
    if (VACIAS.has(palabra)) continue;
    if (palabra.length < TOKEN_MINIMO) continue;
    tokens.push(recortarSufijo(palabra));
  }
  return tokens;
}

/* Vector binario de presencia segun el vocabulario dado.
 * El orden del vocabulario debe ser el mismo del entrenamiento. */
function bolsaDePalabras(texto, vocabulario) {
  const presentes = new Set(normalizar(texto));
  return vocabulario.map((t) => (presentes.has(t) ? 1 : 0));
}

// Exportacion doble: navegador (global) y Node (para la verificacion).
if (typeof module !== "undefined" && module.exports) {
  module.exports = { normalizar, bolsaDePalabras };
}
