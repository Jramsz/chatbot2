/*
 * Acceso a GitHub para el editor del catalogo.
 *
 * El control de acceso lo hace GitHub, no esta pagina: sin un token de una
 * cuenta con permiso de escritura en el repositorio, no se puede leer el
 * catalogo fuente ni guardar nada. Una contrasena escrita en la pagina no
 * protegeria nada, porque cualquiera puede leer el codigo de un sitio
 * estatico.
 *
 * El token solo se envia a api.github.com (ver la politica de seguridad de
 * index.html) y se guarda en sessionStorage: se borra al cerrar la pestana.
 */

const GitHub = (() => {
  const API = "https://api.github.com";

  class ErrorGitHub extends Error {
    constructor(estado, mensaje) {
      super(mensaje);
      this.estado = estado;
    }
  }

  const MENSAJES = {
    401: "El token no es válido o ya venció. Cree uno nuevo (ver la guía).",
    403: "El token no tiene permiso para esta acción en el repositorio.",
    404: "No se encontró el repositorio o el archivo, o el token no tiene acceso a él.",
    409: "Alguien guardó cambios en el catálogo mientras usted editaba. Recargue para ver la versión actual.",
    422: "GitHub rechazó el cambio. Recargue el catálogo e inténtelo de nuevo.",
  };

  async function pedir(token, ruta, opciones = {}) {
    let respuesta;
    try {
      respuesta = await fetch(API + ruta, {
        ...opciones,
        cache: "no-store",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${token}`,
          "X-GitHub-Api-Version": "2022-11-28",
          ...(opciones.body ? { "Content-Type": "application/json" } : {}),
        },
      });
    } catch (e) {
      throw new ErrorGitHub(0, "No hay conexión con GitHub. Revise su conexión a internet.");
    }
    if (!respuesta.ok) {
      throw new ErrorGitHub(
        respuesta.status,
        MENSAJES[respuesta.status] || `GitHub respondió con un error (${respuesta.status}).`
      );
    }
    return respuesta.json();
  }

  // El contenido de los archivos viaja en base64; el catalogo tiene tildes y
  // enes, asi que hay que pasar por UTF-8 (atob/btoa solo manejan Latin-1).
  function aBase64(texto) {
    const bytes = new TextEncoder().encode(texto);
    let binario = "";
    for (let n = 0; n < bytes.length; n += 0x8000) {
      binario += String.fromCharCode(...bytes.subarray(n, n + 0x8000));
    }
    return btoa(binario);
  }

  function deBase64(base64) {
    const binario = atob(base64.replace(/\s/g, ""));
    const bytes = Uint8Array.from(binario, (c) => c.charCodeAt(0));
    return new TextDecoder("utf-8").decode(bytes);
  }

  /* Comprueba el token: quien es y si puede escribir en el repositorio. */
  async function comprobarAcceso(token, repositorio) {
    const [usuario, repo] = await Promise.all([
      pedir(token, "/user"),
      pedir(token, `/repos/${repositorio}`),
    ]);
    return {
      usuario: usuario.login,
      puedeEscribir: Boolean(repo.permissions && repo.permissions.push),
    };
  }

  async function leerArchivo(token, repositorio, rama, ruta) {
    const r = await pedir(token, `/repos/${repositorio}/contents/${ruta}?ref=${encodeURIComponent(rama)}`);
    return { texto: deBase64(r.content), sha: r.sha };
  }

  /* Guarda el archivo como un commit en la rama. `sha` es la version que se
   * leyo: si otra persona guardo despues, GitHub responde 409 y no se pisa
   * su trabajo. */
  async function guardarArchivo(token, repositorio, rama, ruta, texto, sha, mensaje) {
    const r = await pedir(token, `/repos/${repositorio}/contents/${ruta}`, {
      method: "PUT",
      body: JSON.stringify({ message: mensaje, content: aBase64(texto), sha, branch: rama }),
    });
    return { sha: r.content.sha, commit: r.commit.html_url, commitSha: r.commit.sha };
  }

  /* Ultima ejecucion de la publicacion automatica en la rama, o null si el
   * token no tiene permiso para ver Actions (no es imprescindible). */
  async function ultimaPublicacion(token, repositorio, rama) {
    try {
      const r = await pedir(token, `/repos/${repositorio}/actions/runs?branch=${encodeURIComponent(rama)}&per_page=1`);
      const run = r.workflow_runs && r.workflow_runs[0];
      if (!run) return null;
      return { estado: run.status, resultado: run.conclusion, url: run.html_url, sha: run.head_sha, creada: run.created_at };
    } catch (e) {
      return null;
    }
  }

  return { comprobarAcceso, leerArchivo, guardarArchivo, ultimaPublicacion, aBase64, deBase64, ErrorGitHub };
})();

if (typeof module !== "undefined" && module.exports) {
  module.exports = GitHub;
}
