import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";

import { ApiError, api } from "@/lib/cite/api";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      if (mode === "register") await api.register(email.trim(), password);
      else await api.login(email.trim(), password);
      await navigate({ to: "/" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : mode === "register" ? "Could not create the account." : "Could not sign in.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
      <p className="text-xs uppercase tracking-widest text-muted">Personal library</p>
      <h1 className="mt-2 font-serif text-4xl font-semibold">Cite</h1>
      <p className="mt-2 text-sm text-muted">
        Save notes, files, and pages. Ask a question. Every claim has to point at a chunk you stored.
      </p>
      <form onSubmit={submit} className="mt-8 flex flex-col gap-3 rounded-md border border-line bg-sheet p-4">
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            className={`h-11 rounded-md text-sm ${mode === "login" ? "bg-ink text-sienna-ink" : "bg-paper text-muted"}`}
            onClick={() => setMode("login")}
          >
            Sign in
          </button>
          <button
            type="button"
            className={`h-11 rounded-md text-sm ${mode === "register" ? "bg-ink text-sienna-ink" : "bg-paper text-muted"}`}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input
            className="h-11 rounded-md border border-line bg-paper px-3"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Password
          <input
            className="h-11 rounded-md border border-line bg-paper px-3"
            type="password"
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            required
            minLength={mode === "register" ? 8 : 1}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {mode === "register" ? <p className="text-xs text-muted">At least 8 characters. Stored as an argon2 hash.</p> : null}
        {error ? (
          <p className="rounded-md bg-danger-bg px-3 py-2 text-sm text-danger" role="alert">
            {error}
          </p>
        ) : null}
        <button type="submit" disabled={pending} className="h-11 rounded-md bg-sienna text-sm font-medium text-sienna-ink disabled:opacity-60">
          {pending ? "Working…" : mode === "register" ? "Create account" : "Sign in"}
        </button>
      </form>
      <Link to="/" className="mt-6 text-sm text-muted">
        Back to the library
      </Link>
    </main>
  );
}
