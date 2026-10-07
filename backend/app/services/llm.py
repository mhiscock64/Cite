"""Local chat and embedding calls. The client speaks the Ollama-compatible API."""

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI

from app.config import get_settings

_llm: "LLM | None" = None


class ModelUnreachable(RuntimeError):
    """Ollama is down, timed out, or returned an unusable payload."""


class LLM:
    def __init__(self, client: OpenAI | None = None) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = client or OpenAI(
            base_url=settings.ollama_base_url_normalized,
            api_key="ollama",
            timeout=60.0,
            max_retries=0,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = self.client.embeddings.create(model=self.settings.embed_model, input=texts)
        except Exception as exc:
            raise _as_unreachable(exc) from exc
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = [list(item.embedding) for item in ordered]
        expected = self.settings.embed_dim
        if len(vectors) != len(texts) or any(len(vector) != expected for vector in vectors):
            raise ModelUnreachable(f"Embedding model did not return {expected}-dimensional vectors")
        return vectors

    def complete(self, system: str, user: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.settings.chat_model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as exc:
            raise _as_unreachable(exc) from exc
        if not response.choices:
            raise ModelUnreachable("Chat model returned no choices")
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise ModelUnreachable("Chat model returned an empty message")
        return content


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = LLM()
    return _llm


def set_llm(llm: LLM | None) -> None:
    global _llm
    _llm = llm


def _as_unreachable(exc: Exception) -> Exception:
    if isinstance(exc, ModelUnreachable):
        return exc
    if isinstance(exc, (APIError, APIConnectionError, APITimeoutError, TimeoutError, ConnectionError)):
        return ModelUnreachable(str(exc) or exc.__class__.__name__)
    return exc
