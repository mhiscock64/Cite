"""Question answering. /ask returns JSON. /ask/stream emits SSE events."""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.models import User
from app.schemas import AskIn, AskOut
from app.services.answering import AnswerResult, answer_question

router = APIRouter(prefix="/ask", tags=["ask"])


def _payload(result: AnswerResult) -> AskOut:
    return AskOut(
        id=result.id,
        question=result.question,
        answer=result.answer,
        refused=result.refused,
        reason=result.reason,  # type: ignore[arg-type]
        citations=result.citations,
    )


@router.post("", response_model=AskOut)
def ask(body: AskIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> AskOut:
    return _payload(answer_question(db, user.id, body.question))


@router.post("/stream")
def ask_stream(body: AskIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> StreamingResponse:
    result = answer_question(db, user.id, body.question)

    def events():
        if result.reason in {"nothing_matched", "unsupported"}:
            yield _sse(
                {
                    "type": "refusal",
                    "reason": result.reason,
                    "answer": result.answer,
                    "id": str(result.id),
                    "citations": [],
                }
            )
            return
        for token in _tokens(result.answer):
            yield _sse({"type": "token", "text": token})
        yield _sse(
            {
                "type": "done",
                "id": str(result.id),
                "answer": result.answer,
                "refused": result.refused,
                "reason": result.reason,
                "citations": [item.model_dump(mode="json") for item in result.citations],
            }
        )

    return StreamingResponse(events(), media_type="text/event-stream")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _tokens(text: str) -> list[str]:
    if not text:
        return []
    words = text.split(" ")
    tokens: list[str] = []
    for index, word in enumerate(words):
        tokens.append(word if index == len(words) - 1 else word + " ")
    return tokens
