"""Hybrid retrieval: keyword tsvector plus cosine similarity, one Postgres.

Both queries filter to the caller's user_id inside a CTE before they rank.
Keyword and vector hits are merged by chunk id. A keyword hit is lifted to at
least 0.45 because ts_rank_cd is small on short chunks. The chunk score is the
stronger of cosine similarity and that keyword score. Hits under min_score
are dropped, then the top final_k remain.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings


@dataclass(frozen=True)
class Hit:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    heading: str | None
    position: int
    text: str
    score: float


def hybrid_search(db: Session, user_id: UUID, question: str, embedding: list[float] | None) -> list[Hit]:
    settings = get_settings()
    keyword_rows = _keyword_hits(db, user_id, question, settings.keyword_pool)
    vector_rows = _vector_hits(db, user_id, embedding, settings.vector_pool) if embedding is not None else []

    merged: dict[UUID, dict] = {}
    for row in keyword_rows:
        merged[row["id"]] = {**row, "keyword": float(row["rank"]), "cosine": None}
    for row in vector_rows:
        slot = merged.get(row["id"])
        cosine = float(row["cosine"])
        if slot is None:
            merged[row["id"]] = {**row, "keyword": None, "cosine": cosine}
        else:
            slot["cosine"] = cosine

    hits: list[Hit] = []
    for slot in merged.values():
        score = _blend(slot["cosine"], slot["keyword"])
        if score < settings.min_score:
            continue
        hits.append(
            Hit(
                chunk_id=slot["id"],
                document_id=slot["document_id"],
                document_title=slot["document_title"],
                heading=slot["heading"],
                position=slot["position"],
                text=slot["text"],
                score=score,
            )
        )
    hits.sort(key=lambda hit: (-hit.score, hit.position))
    return hits[: settings.final_k]


def _blend(cosine: float | None, keyword: float | None) -> float:
    """Either signal can clear the cutoff. Keyword ranks are tiny, so a real
    tsquery hit is lifted to at least 0.45 before it is compared with cosine.
    """
    scores: list[float] = []
    if cosine is not None:
        scores.append(cosine)
    if keyword is not None and keyword > 0:
        scores.append(max(0.45, min(1.0, keyword * 8.0)))
    if not scores:
        return 0.0
    return max(scores)


def _keyword_hits(db: Session, user_id: UUID, question: str, limit: int) -> list[dict]:
    if not question.strip():
        return []
    rows = db.execute(
        text(
            """
            WITH scoped AS (
                SELECT c.id, c.document_id, c.position, c.heading, c.text, c.tsv,
                       d.title AS document_title
                FROM chunks c
                JOIN documents d ON d.id = c.document_id AND d.user_id = c.user_id
                WHERE c.user_id = :user_id
            ),
            query AS (
                SELECT plainto_tsquery('english', :question) AS q
            )
            SELECT s.id, s.document_id, s.position, s.heading, s.text, s.document_title,
                   ts_rank_cd(s.tsv, query.q) AS rank
            FROM scoped s
            CROSS JOIN query
            WHERE query.q IS NOT NULL
              AND length(query.q::text) > 0
              AND s.tsv @@ query.q
            ORDER BY rank DESC
            LIMIT :limit
            """
        ),
        {"user_id": user_id, "question": question, "limit": limit},
    ).mappings()
    return [dict(row) for row in rows]


def _vector_hits(db: Session, user_id: UUID, embedding: list[float], limit: int) -> list[dict]:
    literal = "[" + ",".join(f"{value:.7f}" for value in embedding) + "]"
    rows = db.execute(
        text(
            """
            WITH scoped AS (
                SELECT c.id, c.document_id, c.position, c.heading, c.text, c.embedding,
                       d.title AS document_title
                FROM chunks c
                JOIN documents d ON d.id = c.document_id AND d.user_id = c.user_id
                WHERE c.user_id = :user_id
                  AND c.embedding IS NOT NULL
            )
            SELECT id, document_id, position, heading, text, document_title,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS cosine
            FROM scoped
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        ),
        {"user_id": user_id, "embedding": literal, "limit": limit},
    ).mappings()
    return [dict(row) for row in rows]
