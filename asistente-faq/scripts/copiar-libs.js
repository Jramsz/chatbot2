// Copia las librerias de node_modules a web/lib. El widget se entrega como
// archivos estaticos, asi que no puede depender de node_modules ni de un CDN.
const fs = require("fs");
const path = require("path");

const destino = path.join(__dirname, "..", "web", "lib");
const origen = path.join(__dirname, "..", "node_modules", "@tensorflow", "tfjs", "dist", "tf.min.js");

fs.mkdirSync(destino, { recursive: true });
fs.copyFileSync(origen, path.join(destino, "tf.min.js"));
console.log("Copiado: web/lib/tf.min.js");
