import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: Vite en el 5173 con proxy de /api hacia el FastAPI en el 8000.
// Build: genera dist/ (lo sirve el FastAPI en producción).
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
});
