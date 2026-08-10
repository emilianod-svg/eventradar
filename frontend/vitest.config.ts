import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  envDir: "..",
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setupTests.ts"],
    // VITE_API_URL de prueba: los tests no dependen del .env real.
    env: {
      VITE_API_URL: "http://localhost:8000",
    },
  },
});
