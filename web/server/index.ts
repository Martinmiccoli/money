// Avvio: API + webapp compilata (web/dist) su 127.0.0.1:8787. Solo locale: l'accesso remoto arriverà
// con Cloudflare Tunnel + Access (M9), mai con una porta aperta.
import { resolve } from "node:path";
import { serve } from "@hono/node-server";
import { serveStatic } from "@hono/node-server/serve-static";
import postgres from "postgres";
import { createApp, REPO } from "./app.js";

try {
  process.loadEnvFile(resolve(REPO, ".env"));
} catch {
  /* .env opzionale se le variabili sono già nell'ambiente */
}
const url = process.env.DATABASE_URL;
if (!url) throw new Error("DATABASE_URL mancante (.env)");

// Le date (tipo SQL `date`, OID 1082) restano stringhe AAAA-MM-GG: niente conversioni di fuso orario.
const sql = postgres(url, {
  max: 4,
  types: { date: { to: 1082, from: [1082], serialize: (x: string) => x, parse: (x: string) => x } },
});
const app = createApp(sql);
app.use("/*", serveStatic({ root: "./dist" }));
app.get("*", serveStatic({ path: "./dist/index.html" }));

const port = Number(process.env.WEB_PORT ?? 8787);
serve({ fetch: app.fetch, port, hostname: "127.0.0.1" }, () =>
  console.log(`money web: http://127.0.0.1:${port}`),
);
