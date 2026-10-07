import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";

import { Shell } from "@/components/cite/shell";
import { ApiError, api, askStream } from "@/lib/cite/api";
import type { AskReason, Citation } from "@/lib/cite/types";

export const Route = createFileRoute("/ask")({
  component: AskPage,
});

function AskPage() {
  const [live, setLive] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  useEffect(() => setLive(true), []);
  const me = useQuery({ queryKey: ["me"], queryFn: () => api.me(), enabled: live });

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [reason, setReason] = useState<AskReason>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setAnswer("");
    setCitations([]);
    setReason(null);
    try {
      await askStream(question.trim(), (streamEvent) => {
        if (streamEvent.type === "token") {
          setAnswer((current) => current + streamEvent.text);
          return;
        }
        if (streamEvent.type === "refusal") {
          setReason(streamEvent.reason);
          setAnswer(streamEvent.answer);
          setCitations([]);
          return;
        }
        setReason(streamEvent.reason);
        setAnswer(streamEvent.answer);
        setCitations(streamEvent.citations);
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The question did not go through.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Shell
      user={me.data ?? null}
      onSignOut={() => {
        queryClient.clear();
        void navigate({ to: "/login" });
      }}
    >
      <h1 className="font-serif text-3xl font-semibold">Ask</h1>
      <p className="mt-1 max-w-xl text-sm text-muted">
        Answers are written only from chunks in your library. If nothing qualifies, the model is not called.
      </p>
      {live && me.isError ? (
        <p className="mt-6 text-sm">
          <Link to="/login" className="text-sienna">
            Sign in
          </Link>{" "}
          before asking.
        </p>
      ) : null}
      {me.data ? (
        <form onSubmit={submit} className="mt-5 flex flex-col gap-3">
          <textarea
            className="min-h-28 rounded-md border border-line bg-sheet px-3 py-2 text-sm"
            placeholder="What did I save about session cookies?"
            required
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />
          <button type="submit" disabled={pending} className="h-11 rounded-md bg-sienna text-sm font-medium text-sienna-ink disabled:opacity-60 sm:w-40">
            {pending ? "Reading…" : "Ask"}
          </button>
        </form>
      ) : null}
      {error ? (
        <p className="mt-4 rounded-md bg-danger-bg px-3 py-2 text-sm text-danger" role="alert">
          {error}
        </p>
      ) : null}
      <AnswerPanel reason={reason} answer={answer} citations={citations} pending={pending} />
    </Shell>
  );
}

function AnswerPanel({
  reason,
  answer,
  citations,
  pending,
}: {
  reason: AskReason;
  answer: string;
  citations: Citation[];
  pending: boolean;
}) {
  if (!answer && !pending && !reason) {
    return (
      <section className="mt-8 rounded-md border border-dashed border-line px-4 py-8">
        <h2 className="font-serif text-xl">Nothing asked yet</h2>
        <p className="mt-1 text-sm text-muted">A matching chunk opens beside the answer. Invented sources are dropped.</p>
      </section>
    );
  }
  if (reason === "nothing_matched") {
    return (
      <section className="mt-6 rounded-md border border-line bg-sheet px-4 py-5">
        <h2 className="font-serif text-xl">Nothing in your library matches.</h2>
        <p className="mt-1 text-sm text-muted">No chunk cleared the cutoff, so the chat model was not called.</p>
      </section>
    );
  }
  if (reason === "unsupported") {
    return (
      <section className="mt-6 rounded-md border border-line bg-sheet px-4 py-5">
        <h2 className="font-serif text-xl">The library does not support an answer.</h2>
        <p className="mt-1 text-sm text-muted">The model did not cite a retrieved chunk, so the answer was replaced.</p>
      </section>
    );
  }
  return (
    <div className="mt-6 grid gap-4 lg:grid-cols-3">
      <article className="rounded-md border border-line bg-sheet px-4 py-4 lg:col-span-2">
        {reason === "model_unreachable" ? (
          <p className="mb-3 rounded-md bg-warn-bg px-3 py-2 text-sm text-warn">
            Model unreachable. Showing keyword excerpts instead of a generated answer.
          </p>
        ) : null}
        <h2 className="font-serif text-xl">Answer</h2>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6">{answer || (pending ? "…" : "")}</p>
      </article>
      <aside className="flex flex-col gap-2">
        <h2 className="font-serif text-lg">Citations</h2>
        {citations.length === 0 ? <p className="text-sm text-muted">{pending ? "Waiting for sources." : "No citations."}</p> : null}
        {citations.map((citation) => (
          <Link
            key={citation.chunk_id}
            to="/documents/$id"
            params={{ id: citation.document_id }}
            hash={`chunk-${citation.chunk_id}`}
            className="rounded-md border border-line bg-sheet px-3 py-3 text-sm hover:border-sienna"
          >
            <span className="block font-medium">{citation.document_title}</span>
            <span className="mt-1 block text-xs text-muted">
              {citation.heading || "No heading"} · score {citation.score.toFixed(2)}
            </span>
            <span className="mt-2 block text-muted">{citation.text.slice(0, 180)}</span>
          </Link>
        ))}
      </aside>
    </div>
  );
}
