import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 5173,
    hmr: {
      overlay: false,
    },
    proxy: {
      "/api/auth": "http://localhost:8080",
      "/api/v1/customers": "http://localhost:8082",
      "/api/v1/disputes": "http://localhost:8082",
      "/api/v1/credit": "http://localhost:8080",
      "/api/v1/dashboard": "http://localhost:8080",
      "/api/v1/crb": "http://localhost:8080",
      "/api/v1/models": "http://localhost:8080",
      "/api/v1/audit": "http://localhost:8080",
      "/api/v1/admin": "http://localhost:8081",
      "/api/v1/notifications": "http://localhost:8085",
      "/api/v1/media": "http://localhost:8083",
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
