import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { Shell, StatusMark } from "@/components/cite/shell";
import { ApiError, api } from "@/lib/cite/api";

export const Route = createFileRoute("/documents/$id")({
  component: DocumentPage,
});

function DocumentPage() {
  const { id } = Route.useParams();
  const [live, setLive] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  useEffect(() => setLive(true), []);
  const me = useQuery({ queryKey: ["me"], queryFn: () => api.me(), enabled: live });
  const doc = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.document(id),
    enabled: live && Boolean(me.data),
    refetchInterval: (query) => (query.state.data?.status === "queued" ? 1200 : false),
  });

  useEffect(() => {
    if (!doc.data) return;
    const hash = window.location.hash.replace("#", "");
    if (!hash) return;
    document.getElementById(hash)?.scrollIntoView({ block: "start" });
  }, [doc.data]);

  async function remove() {
    await api.remove(id);
    await queryClient.invalidateQueries({ queryKey: ["documents"] });
    await navigate({ to: "/" });
  }

  const missing = doc.error instanceof ApiError && doc.error.status === 404;

  return (
    <Shell
      user={me.data ?? null}
      onSignOut={() => {
        queryClient.clear();
        void navigate({ to: "/login" });
      }}
    >
      <Link to="/" className="text-sm text-muted">
        Library
      </Link>
      {!live || doc.isLoading ? <h1 className="mt-3 font-serif text-3xl">Opening source…</h1> : null}
      {missing ? (
        <section className="mt-4 rounded-md border border-line bg-sheet px-4 py-5">
          <h1 className="font-serif text-2xl">Document not found</h1>
          <p className="mt-1 text-sm text-muted">It is gone, or it belongs to another account.</p>
        </section>
      ) : null}
      {doc.data ? (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h1 className="font-serif text-3xl font-semibold">{doc.data.title}</h1>
            <StatusMark status={doc.data.status} />
          </div>
          <p className="mt-2 text-xs uppercase tracking-wide text-muted">
            {doc.data.source_type}
            {doc.data.source_url ? ` · ${doc.data.source_url}` : ""}
          </p>
          {doc.data.status === "failed" ? (
            <p className="mt-4 rounded-md bg-danger-bg px-3 py-2 text-sm text-danger">Ingest failed. {doc.data.error}</p>
          ) : null}
          {doc.data.status === "queued" ? <p className="mt-4 text-sm text-muted">Queued. Extracting, chunking, and embedding.</p> : null}
          <ol className="mt-6 flex flex-col gap-3">
            {doc.data.chunks.map((chunk) => (
              <li key={chunk.id} id={`chunk-${chunk.id}`} className="scroll-mt-6 rounded-md border border-line bg-sheet px-4 py-3">
                <p className="text-xs uppercase tracking-wide text-muted">
                  {chunk.position + 1}
                  {chunk.heading ? ` · ${chunk.heading}` : ""}
                </p>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6">{chunk.text}</p>
              </li>
            ))}
          </ol>
          <button type="button" className="mt-6 h-11 text-sm text-danger" onClick={() => void remove()}>
            Delete document
          </button>
        </>
      ) : null}
    </Shell>
  );
}
