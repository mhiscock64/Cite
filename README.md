# Cite

A personal knowledge base. You save notes, files, and URLs. You ask a question. The answer has to cite chunks from your library, or it is refused.

One account. No teams, no OAuth, no Redis, no second model provider, no paid API. Chat and embeddings run locally through Ollama.

## Layout

| Path | What it is |
| --- | --- |
| `backend/` | FastAPI, SQLAlchemy 2, Alembic, pytest |
| `src/` | React + Vite + TypeScript client |
| `docker-compose.yml` | Postgres 16 (pgvector) and the API |

Ollama stays on the host. It is not a compose service.

## Run it

```bash
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text

cp .env.example .env
docker compose up --build
```

The API listens on port 8000 and migrates on startup. Compose reaches Ollama at `http://host.docker.internal:11434/v1`.

In another terminal, from the repo root:

```bash
npm install
npm run dev
```

The Vite dev server proxies `/auth`, `/documents`, and `/ask` to the API so the session cookie stays same-origin. Open the app, register, and save something.

Defaults:

| Variable | Default |
| --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` |
| `CHAT_MODEL` | `qwen2.5:7b-instruct` |
| `EMBED_MODEL` | `nomic-embed-text` |
| Embedding size | 768 |

The chat client uses that base URL. There is no other provider.

## Data

- `users` — email, argon2 password hash
- `sessions` — sha256 of an opaque cookie token. The cookie is HTTP-only.
- `documents` — `text`, `url`, or `file`. Status is `queued`, `ready`, or `failed`.
- `ingest_jobs` — the background job row the worker updates
- `chunks` — heading path, position, text, generated `tsvector`, `vector(768)`
- `questions` — what was asked and the answer that was actually returned

GIN index on `chunks.tsv`. HNSW index on `chunks.embedding` (`vector_cosine_ops`). Every read filters `user_id` inside a CTE before ranking. Another user's document is a 404, not a 403.

Files (`.txt`, `.md`, `.pdf`, max 10 MB) are stored on disk under `FILE_STORAGE_DIR/<user_id>/<document_id>/`. PDF text comes from pypdf. They are not stored in Postgres.

## Ingest

`POST /documents` (text or URL) and `POST /documents/upload` insert the document as `queued` and an `ingest_jobs` row, then return. A FastAPI `BackgroundTasks` job extracts, chunks, embeds in batches, and sets the document to `ready` or `failed` with `error`. The client polls `GET /documents/{id}`.

URL fetch is server-side only: 10s timeout, 2 MB cap, at most 2 redirects. Private, loopback, and link-local addresses are rejected before the request and again after each redirect. Main content is extracted with trafilatura.

If Ollama is down during ingest, chunks are still saved with a null embedding and the document becomes `ready`. Keyword search keeps working.

## Chunking

Token counts are `len(text) / 4`.

- If the source has markdown headings, split on those and store the heading path (`Guide > Install`).
- Otherwise split on blank-line paragraphs.
- Pack pieces toward 500–800 tokens.
- A piece larger than 800 tokens is windowed first.
- Neighbors overlap by about 80 tokens.

## Hybrid retrieval

1. Embed the question with `nomic-embed-text` when Ollama is up.
2. Top 20 keyword hits: `plainto_tsquery` + `ts_rank_cd`, scoped with `WHERE user_id = ?` before `ORDER BY`.
3. Top 20 vector hits: cosine distance `<=>`, same user scope, null embeddings skipped.
4. Merge on chunk id. A lexical hit is lifted to at least 0.45, because `ts_rank_cd` on a short chunk is tiny. The score is the stronger of cosine similarity and that keyword score.
5. Keep at most 5 hits with score ≥ 0.20 (`min_score`).

## Answering and refusal

If nothing clears the cutoff, the chat model is not called. The API returns `Nothing in your library matches.` and no citations (`reason: nothing_matched`).

If chunks match, the chat model sees only those excerpts. The system prompt tells it to answer only from the excerpts, to say so when they do not contain the answer, to cite chunk ids from the context, and not to use outside knowledge. It must return JSON: `{"answer", "cited_chunk_ids"}`.

Cited ids that were not in the retrieved set are dropped. If none remain, the answer is replaced with `The library does not support an answer.` and the citations are empty (`reason: unsupported`).

`POST /ask` returns that final JSON. `POST /ask/stream` sends `token` events and then a `done` event with citations, or a `refusal` event when retrieval or citation checks fail. The model is called before tokens are emitted, so a rejected citation never streams.

## When Ollama is down

Saving documents and keyword search still work. `/ask` does not raise. It returns a stitched extractive summary of the keyword hits, with those chunks as citations, and `reason: model_unreachable`. The client shows that as its own state, separate from "nothing matched" and "the library does not support an answer."

## Tests

```bash
cd backend
uv venv --python 3.12
uv pip install -e ".[dev]"
uv run pytest
```

Pytest uses Postgres (`cite_test`) and mocks the chat and embedding clients. Covered:

- register, login, logout, unauthenticated 401
- another user's document is 404 and does not appear in their search
- text and PDF ingest, rejected file types, job row reaches `ready`
- SSRF rejection for private, loopback, and link-local URLs, including a redirect onto loopback, with no fetch of the blocked address
- empty retrieval returns the refusal and does not call the chat model
- a citation id the model invented is dropped; if none of the ids were retrieved, the answer is replaced

## API

- `POST /auth/register` `POST /auth/login` `POST /auth/logout` `GET /auth/me`
- `POST /documents` `POST /documents/upload` `GET /documents` `GET /documents/{id}` `DELETE /documents/{id}`
- `POST /ask` `POST /ask/stream`
