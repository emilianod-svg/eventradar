import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// EventRadar carga las variables de entorno desde la raíz del repositorio
// (un único .env.example compartido con el backend), no desde frontend/.env.
export default defineConfig({
  plugins: [react()],
  envDir: "..",
  envPrefix: "VITE_",
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/ready": "http://localhost:8000",
    },
  },
});
