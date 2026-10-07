"""Request and response models."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class DocumentCreate(BaseModel):
    source_type: Literal["text", "url"]
    title: str | None = Field(default=None, max_length=200)
    text: str | None = Field(default=None, max_length=1_000_000)
    url: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def required_payload(self) -> "DocumentCreate":
        if self.source_type == "text" and not (self.text and self.text.strip()):
            raise ValueError("text is required")
        if self.source_type == "url" and not (self.url and self.url.strip()):
            raise ValueError("url is required")
        return self


class ChunkOut(BaseModel):
    id: UUID
    position: int
    heading: str | None
    text: str


class DocumentOut(BaseModel):
    id: UUID
    title: str
    source_type: Literal["text", "url", "file"]
    source_url: str | None
    status: Literal["queued", "ready", "failed"]
    error: str | None
    created_at: datetime
    chunk_count: int = 0


class DocumentDetail(DocumentOut):
    chunks: list[ChunkOut]


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class CitationOut(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    heading: str | None
    position: int
    text: str
    score: float


class AskOut(BaseModel):
    id: UUID
    question: str
    answer: str
    refused: bool
    reason: Literal["nothing_matched", "unsupported", "model_unreachable"] | None = None
    citations: list[CitationOut]
