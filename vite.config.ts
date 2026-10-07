import { existsSync } from "node:fs";
import http from "node:http";
import type { Plugin } from "vite";
import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

/**
 * Proxy library routes to the API. Prefer the unix socket used in local
 * dev, and fall back to port 8000 for docker compose.
 */
function citeApiProxy(): Plugin {
  const socketPath = process.env.CITE_API_SOCKET || "/tmp/cite-api.sock";
  return {
    name: "cite-api-proxy",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const rawUrl = req.url ?? "/";
        const pathOnly = rawUrl.split("?", 1)[0] ?? "";
        const isApi =
          pathOnly === "/auth" ||
          pathOnly.startsWith("/auth/") ||
          pathOnly === "/documents" ||
          pathOnly.startsWith("/documents/") ||
          pathOnly === "/ask" ||
          pathOnly.startsWith("/ask/");
        if (!isApi) {
          next();
          return;
        }
        const method = (req.method ?? "GET").toUpperCase();
        const accept = String(req.headers.accept ?? "");
        if (
          (method === "GET" || method === "HEAD") &&
          accept.includes("text/html") &&
          !pathOnly.startsWith("/auth")
        ) {
          next();
          return;
        }

        const headers = { ...req.headers };
        delete headers.connection;
        const target = existsSync(socketPath)
          ? { socketPath, path: rawUrl, method: req.method, headers }
          : { hostname: "127.0.0.1", port: 8000, path: rawUrl, method: req.method, headers };
        const upstream = http.request(target, (incoming) => {
          res.writeHead(incoming.statusCode ?? 502, incoming.headers);
          incoming.pipe(res);
        });
        upstream.on("error", () => {
          if (res.headersSent) return;
          res.statusCode = 502;
          res.setHeader("content-type", "application/json");
          res.end(JSON.stringify({ detail: "The library service is not running." }));
        });
        req.pipe(upstream);
      });
    },
  };
}

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 8080,
    strictPort: true,
    allowedHosts: true,
  },
  resolve: { tsconfigPaths: true },
  plugins: [citeApiProxy(), tailwindcss(), tanstackStart(), viteReact()],
});
