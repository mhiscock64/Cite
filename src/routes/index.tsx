import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";

import { Shell, StatusMark } from "@/components/cite/shell";
import { ApiError, api } from "@/lib/cite/api";
import type { User } from "@/lib/cite/types";

export const Route = createFileRoute("/")({
  component: LibraryPage,
});

function LibraryPage() {
  const [live, setLive] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  useEffect(() => setLive(true), []);

  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api.me(),
    enabled: live,
  });
  const user = me.data ?? null;

  return (
    <Shell
      user={user}
      onSignOut={() => {
        queryClient.clear();
        void navigate({ to: "/login" });
      }}
    >
      <header className="mb-5 flex items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-3xl font-semibold">Library</h1>
          <p className="mt-1 text-sm text-muted">Notes, files, and pages you can cite later.</p>
        </div>
      </header>
      {!live || me.isLoading ? <p className="text-sm text-muted">Opening your library…</p> : null}
      {live && me.isError ? <SignedOut /> : null}
      {user ? <Library user={user} /> : null}
    </Shell>
  );
}

function SignedOut() {
  return (
    <section className="rounded-md border border-line bg-sheet p-4">
      <h2 className="font-serif text-xl">Sign in to open your library</h2>
      <p className="mt-1 text-sm text-muted">This library belongs to one account. Nothing is shared.</p>
      <Link to="/login" className="mt-4 inline-flex h-11 items-center rounded-md bg-sienna px-4 text-sm font-medium text-sienna-ink">
        Sign in or register
      </Link>
    </section>
  );
}

function Library({ user }: { user: User }) {
  const queryClient = useQueryClient();
  const docs = useQuery({
    queryKey: ["documents", user.id],
    queryFn: () => api.documents(),
    refetchInterval: (query) => (query.state.data?.some((doc) => doc.status === "queued") ? 1200 : false),
  });
  const [tab, setTab] = useState<"note" | "url" | "file">("note");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ["documents", user.id] });
  }

  async function saveNote(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api.addText(text, title);
      setText("");
      setTitle("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the note.");
    } finally {
      setPending(false);
    }
  }

  async function saveUrl(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api.addUrl(url, title);
      setUrl("");
      setTitle("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the URL.");
    } finally {
      setPending(false);
    }
  }

  async function saveFile(event: FormEvent) {
    event.preventDefault();
    const input = (event.target as HTMLFormElement).elements.namedItem("file");
    const file = input instanceof HTMLInputElement ? input.files?.[0] : undefined;
    if (!file) return;
    setPending(true);
    setError(null);
    try {
      await api.upload(file);
      (event.target as HTMLFormElement).reset();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not upload the file.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-md border border-line bg-sheet p-4">
        <div className="grid grid-cols-3 gap-2">
          {(
            [
              ["note", "Paste"],
              ["url", "URL"],
              ["file", "File"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={`h-11 rounded-md text-sm ${tab === key ? "bg-ink text-sienna-ink" : "bg-paper text-muted"}`}
              onClick={() => {
                setTab(key);
                setError(null);
              }}
            >
              {label}
            </button>
          ))}
        </div>
        {tab === "note" ? (
          <form onSubmit={saveNote} className="mt-3 flex flex-col gap-3">
            <input
              className="h-11 rounded-md border border-line bg-paper px-3 text-sm"
              placeholder="Title, optional"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
            <textarea
              className="min-h-32 rounded-md border border-line bg-paper px-3 py-2 text-sm"
              placeholder="Paste a note. Headings become the chunk path."
              required
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
            <button type="submit" disabled={pending} className="h-11 rounded-md bg-sienna text-sm font-medium text-sienna-ink disabled:opacity-60">
              {pending ? "Saving…" : "Save note"}
            </button>
          </form>
        ) : null}
        {tab === "url" ? (
          <form onSubmit={saveUrl} className="mt-3 flex flex-col gap-3">
            <input
              className="h-11 rounded-md border border-line bg-paper px-3 text-sm"
              placeholder="https://"
              type="url"
              required
              value={url}
              onChange={(event) => setUrl(event.target.value)}
            />
            <p className="text-xs text-muted">Fetched on the server. Private and loopback addresses are rejected.</p>
            <button type="submit" disabled={pending} className="h-11 rounded-md bg-sienna text-sm font-medium text-sienna-ink disabled:opacity-60">
              {pending ? "Saving…" : "Save URL"}
            </button>
          </form>
        ) : null}
        {tab === "file" ? (
          <form onSubmit={saveFile} className="mt-3 flex flex-col gap-3">
            <input name="file" type="file" accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf" required className="text-sm" />
            <p className="text-xs text-muted">.txt, .md, or .pdf. 10 MB max. The file stays on disk, not in the database.</p>
            <button type="submit" disabled={pending} className="h-11 rounded-md bg-sienna text-sm font-medium text-sienna-ink disabled:opacity-60">
              {pending ? "Uploading…" : "Upload"}
            </button>
          </form>
        ) : null}
        {error ? (
          <p className="mt-3 rounded-md bg-danger-bg px-3 py-2 text-sm text-danger" role="alert">
            {error}
          </p>
        ) : null}
      </section>

      {docs.isLoading ? <p className="text-sm text-muted">Loading documents…</p> : null}
      {docs.data && docs.data.length === 0 ? (
        <section className="rounded-md border border-dashed border-line px-4 py-8 text-center">
          <h2 className="font-serif text-xl">Nothing saved yet</h2>
          <p className="mt-1 text-sm text-muted">Paste a note, drop a PDF, or add a URL.</p>
        </section>
      ) : null}
      <ul className="flex flex-col gap-2">
        {docs.data?.map((doc) => (
          <li key={doc.id} className="rounded-md border border-line bg-sheet">
            <Link to="/documents/$id" params={{ id: doc.id }} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <span className="min-w-0">
                <span className="block truncate font-medium">{doc.title}</span>
                <span className="text-xs uppercase tracking-wide text-muted">
                  {doc.source_type}
                  {doc.chunk_count ? ` · ${doc.chunk_count} chunks` : ""}
                </span>
              </span>
              <StatusMark status={doc.status} />
            </Link>
            {doc.status === "failed" && doc.error ? (
              <p className="border-t border-line bg-danger-bg px-4 py-2 text-sm text-danger">Ingest failed. {doc.error}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
