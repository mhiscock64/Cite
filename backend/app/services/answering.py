"""Answer a question from retrieved excerpts, or refuse.

The chat model sees only the merged hits. It must return JSON with an answer
and chunk ids. Ids that were not retrieved are dropped. If none remain, the
answer is replaced and no citations are returned. If retrieval finds nothing
above the cutoff, the chat model is not called.

When Ollama cannot embed or chat, keyword hits are stitched into an extractive
summary. That path does not raise.
"""

import json
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Question
from app.schemas import CitationOut
from app.services.llm import ModelUnreachable, get_llm
from app.services.retrieval import Hit, hybrid_search

NOTHING_MATCHED = "Nothing in your library matches."
UNSUPPORTED = "The library does not support an answer."

SYSTEM_PROMPT = (
    "Answer only from the excerpts. "
    "If they do not contain the answer, say so. "
    "Every claim must cite chunk ids from the context. "
    "Do not use outside knowledge. "
    'Respond with a JSON object {"answer": string, "cited_chunk_ids": string[]} and no other text. '
    "Copy cited_chunk_ids from the excerpt ids."
)


@dataclass
class AnswerResult:
    id: UUID
    question: str
    answer: str
    refused: bool
    reason: str | None
    citations: list[CitationOut]
    chat_called: bool


def answer_question(db: Session, user_id: UUID, question: str) -> AnswerResult:
    text = question.strip()
    embedding, embed_failed = _embed_question(text)
    hits = hybrid_search(db, user_id, text, embedding)
    if not hits:
        return _store(
            db,
            user_id,
            text,
            NOTHING_MATCHED,
            refused=True,
            reason="nothing_matched",
            citations=[],
            chat_called=False,
        )

    # Embeddings down usually means the chat model is down too. Try once, then
    # fall back to the keyword excerpts instead of failing the request.
    if embed_failed:
        try:
            raw = get_llm().complete(SYSTEM_PROMPT, _user_prompt(text, hits))
            chat_called = True
        except ModelUnreachable:
            return _fallback(db, user_id, text, hits)
    else:
        try:
            raw = get_llm().complete(SYSTEM_PROMPT, _user_prompt(text, hits))
            chat_called = True
        except ModelUnreachable:
            return _fallback(db, user_id, text, hits)

    parsed = _parse_model_json(raw)
    allowed = {str(hit.chunk_id): hit for hit in hits}
    cited_ids: list[str] = []
    if parsed is not None:
        for chunk_id in parsed["cited_chunk_ids"]:
            if chunk_id in allowed and chunk_id not in cited_ids:
                cited_ids.append(chunk_id)
        answer_text = parsed["answer"].strip()
    else:
        answer_text = ""

    if not cited_ids or not answer_text:
        return _store(
            db,
            user_id,
            text,
            UNSUPPORTED,
            refused=True,
            reason="unsupported",
            citations=[],
            chat_called=chat_called,
        )

    citations = [_citation(allowed[chunk_id]) for chunk_id in cited_ids]
    return _store(
        db,
        user_id,
        text,
        answer_text,
        refused=False,
        reason=None,
        citations=citations,
        chat_called=chat_called,
    )


def _embed_question(question: str) -> tuple[list[float] | None, bool]:
    try:
        vectors = get_llm().embed([question])
    except ModelUnreachable:
        return None, True
    return vectors[0], False


def _fallback(db: Session, user_id: UUID, question: str, hits: list[Hit]) -> AnswerResult:
    return _store(
        db,
        user_id,
        question,
        _stitch(hits),
        refused=False,
        reason="model_unreachable",
        citations=[_citation(hit) for hit in hits],
        chat_called=False,
    )


def _stitch(hits: list[Hit]) -> str:
    blocks: list[str] = []
    for hit in hits:
        label = hit.heading or hit.document_title
        snippet = hit.text.strip()
        if len(snippet) > 700:
            clipped = snippet[:700]
            snippet = clipped.rsplit(" ", 1)[0] + "…" if " " in clipped else clipped + "…"
        blocks.append(f"{label}\n{snippet}")
    return (
        "The model is unreachable. These are the closest keyword matches in your library:\n\n"
        + "\n\n".join(blocks)
    )


def _user_prompt(question: str, hits: list[Hit]) -> str:
    excerpts = []
    for hit in hits:
        heading = hit.heading or "(none)"
        excerpts.append(f"chunk_id={hit.chunk_id}\nheading: {heading}\n{hit.text}")
    joined = "\n\n".join(excerpts)
    return f"Excerpts:\n\n{joined}\n\nQuestion: {question}"


def _parse_model_json(content: str) -> dict | None:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = _loads(text)
    if data is None:
        match = re.search(r"\{.*\}", text, flags=re.S)
        data = _loads(match.group(0)) if match else None
    if not isinstance(data, dict):
        return None
    answer = data.get("answer")
    raw_ids = data.get("cited_chunk_ids", data.get("citations", []))
    if not isinstance(answer, str) or not isinstance(raw_ids, list):
        return None
    ids = [str(item) for item in raw_ids if isinstance(item, (str, int))]
    return {"answer": answer, "cited_chunk_ids": ids}


def _loads(text: str) -> dict | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _citation(hit: Hit) -> CitationOut:
    return CitationOut(
        chunk_id=hit.chunk_id,
        document_id=hit.document_id,
        document_title=hit.document_title,
        heading=hit.heading,
        position=hit.position,
        text=hit.text,
        score=round(hit.score, 4),
    )


def _store(
    db: Session,
    user_id: UUID,
    question: str,
    answer: str,
    *,
    refused: bool,
    reason: str | None,
    citations: list[CitationOut],
    chat_called: bool,
) -> AnswerResult:
    row = Question(user_id=user_id, question=question, answer=answer, refused=refused)
    db.add(row)
    db.commit()
    db.refresh(row)
    return AnswerResult(
        id=row.id,
        question=question,
        answer=answer,
        refused=refused,
        reason=reason,
        citations=citations,
        chat_called=chat_called,
    )
