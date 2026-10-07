"""Split a document into citation-sized chunks.

Headings win when the source has markdown headings. Otherwise we split on
blank-line paragraphs. Pieces are packed toward 500–800 tokens (about 4
characters per token) with an 80-token overlap between neighbors.
"""

from dataclasses import dataclass
import re

TOKEN_MIN = 500
TOKEN_MAX = 800
TOKEN_OVERLAP = 80

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class ChunkDraft:
    position: int
    heading: str | None
    text: str


def token_len(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def chunk_document(raw: str) -> list[ChunkDraft]:
    text = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    pieces = _pieces(text)
    merged = _pack(pieces)
    return [ChunkDraft(i, heading or None, body) for i, (heading, body) in enumerate(merged)]


def _pieces(text: str) -> list[tuple[str, str]]:
    units = _split_units(text)
    pieces: list[tuple[str, str]] = []
    for heading, body in units:
        body = body.strip()
        if not body:
            continue
        if token_len(body) <= TOKEN_MAX:
            pieces.append((heading, body))
            continue
        for part in _windows(body, TOKEN_MAX, TOKEN_OVERLAP):
            pieces.append((heading, part))
    return pieces


def _split_units(text: str) -> list[tuple[str, str]]:
    if re.search(r"(?m)^#{1,6}\s+\S", text):
        return _split_headings(text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return [("", p) for p in paragraphs] or [("", text)]


def _split_headings(text: str) -> list[tuple[str, str]]:
    stack: list[tuple[int, str]] = []
    buf: list[str] = []
    sections: list[tuple[str, str]] = []

    def path() -> str:
        return " > ".join(title for _, title in stack)

    def flush() -> None:
        body = "\n".join(buf).strip()
        heading = path()
        if body:
            sections.append((heading, body))
        elif heading:
            sections.append((heading, heading.split(" > ")[-1]))

    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            if buf or stack:
                flush()
            buf = []
            level = len(match.group(1))
            title = match.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            continue
        buf.append(line)
    flush()
    return [(h, b) for h, b in sections if b.strip()]


def _windows(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    spans: list[str] = []
    start = 0
    total = len(words)
    while start < total:
        end = start + 1
        while end < total and token_len(" ".join(words[start : end + 1])) <= size:
            end += 1
        spans.append(" ".join(words[start:end]))
        if end >= total:
            break
        next_start = end
        while next_start > start + 1 and token_len(" ".join(words[next_start - 1 : end])) < overlap:
            next_start -= 1
        # Keep at least one new word so a large overlap cannot stall.
        if next_start <= start:
            next_start = start + 1
        if next_start >= end:
            next_start = end
        start = next_start
    return spans


def _tail(text: str, tokens: int) -> str:
    words = text.split()
    if not words or tokens <= 0:
        return ""
    start = len(words)
    while start > 0 and token_len(" ".join(words[start - 1 :])) < tokens:
        start -= 1
    if start == len(words):
        start = len(words) - 1
    return " ".join(words[start:])


def _pack(pieces: list[tuple[str, str]]) -> list[tuple[str, str]]:
    merged: list[tuple[str, str]] = []
    parts: list[str] = []
    headings: list[str] = []

    def body() -> str:
        return "\n\n".join(parts).strip()

    def heading_label() -> str:
        seen: list[str] = []
        for item in headings:
            if item and item not in seen:
                seen.append(item)
        return " | ".join(seen)

    def flush(keep_overlap: bool) -> None:
        nonlocal parts, headings
        text = body()
        if not text:
            parts = []
            headings = []
            return
        label = heading_label()
        merged.append((label, text))
        if keep_overlap:
            overlap = _tail(text, TOKEN_OVERLAP)
            parts = [overlap] if overlap else []
            headings = [label] if label and overlap else []
        else:
            parts = []
            headings = []

    for heading, part in pieces:
        if not parts:
            parts = [part]
            headings = [heading] if heading else []
            continue
        candidate = "\n\n".join([*parts, part]).strip()
        if token_len(candidate) <= TOKEN_MAX:
            parts.append(part)
            if heading:
                headings.append(heading)
            continue
        # Current buffer is large enough, or the next piece simply does not fit.
        if token_len(body()) >= TOKEN_MIN or token_len(part) > TOKEN_MIN:
            flush(keep_overlap=True)
        if parts:
            trial = "\n\n".join([*parts, part]).strip()
            if token_len(trial) > TOKEN_MAX:
                parts = []
                headings = []
        parts.append(part)
        if heading:
            headings.append(heading)
        if token_len(body()) > TOKEN_MAX and len(parts) > 1:
            overlap = parts[0]
            parts = parts[1:]
            headings = [heading] if heading else []
            if token_len(body()) > TOKEN_MAX:
                parts = [part]
                _ = overlap

    if parts:
        text = body()
        if text and not (merged and text == _tail(merged[-1][1], token_len(text))):
            merged.append((heading_label(), text))
    return merged
