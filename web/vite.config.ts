import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In sviluppo Vite (5173) inoltra /api al server Hono (8787). In produzione Hono serve web/dist.
export default defineConfig({
  root: "client",
  plugins: [react()],
  build: { outDir: "../dist", emptyOutDir: true },
  server: { proxy: { "/api": "http://127.0.0.1:8787" } },
});
