import { createFileRoute } from "@tanstack/react-router";

// Production builds have no FastAPI process behind them. Dev proxies /auth to
// the API before this route runs. A 401 (not a 404) matches the real contract
// when the cookie is missing.
export const Route = createFileRoute("/auth/me")({
  server: {
    handlers: {
      GET: async () => Response.json({ detail: "Not authenticated" }, { status: 401 }),
    },
  },
});
