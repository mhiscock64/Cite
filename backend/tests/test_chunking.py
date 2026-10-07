"""Heading-aware chunks stay inside the token budget and overlap."""

from app.services.chunking import TOKEN_MAX, TOKEN_MIN, TOKEN_OVERLAP, chunk_document, token_len


def test_short_note_is_one_chunk():
    chunks = chunk_document("A single paragraph about sessions.")
    assert len(chunks) == 1
    assert chunks[0].position == 0
    assert chunks[0].heading is None


def test_headings_are_kept_on_the_chunk():
    text = "# Guide\n\nIntro paragraph.\n\n## Install\n\nRun the migration.\n"
    chunks = chunk_document(text)
    headings = [chunk.heading for chunk in chunks]
    assert any(heading and "Guide" in heading for heading in headings)
    assert any(heading and "Install" in heading for heading in headings)


def test_long_text_respects_the_budget_and_overlaps():
    paragraph = " ".join(f"word{i}" for i in range(4000))
    chunks = chunk_document(paragraph)
    assert len(chunks) > 2
    for chunk in chunks[:-1]:
        assert token_len(chunk.text) <= TOKEN_MAX
        assert token_len(chunk.text) >= TOKEN_MIN - TOKEN_OVERLAP
    assert token_len(chunks[-1].text) <= TOKEN_MAX
    # Neighboring chunks share an overlap tail.
    previous_tail = chunks[0].text.split()[-12:]
    assert any(word in chunks[1].text.split() for word in previous_tail)
