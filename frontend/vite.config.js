import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In production the app is served by Django/WhiteNoise, whose static files
// live under /static/. In dev, Vite serves from the root.
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/" : "/",
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
}));
