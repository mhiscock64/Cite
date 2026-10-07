"""Server-side URL fetch with a hard size cap and manual redirects."""

from urllib.parse import urljoin

import httpx

from app.services.ssrf import SSRFError, ensure_public_http_url

MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 2
TIMEOUT = 10.0
USER_AGENT = "CiteBot/1.0"
_REDIRECTS = {301, 302, 303, 307, 308}


class FetchError(ValueError):
    pass


def fetch_public_url(url: str, client: httpx.Client | None = None) -> tuple[bytes, str]:
    """Return (body, final_url). Raises SSRFError before any blocked request."""
    owns_client = client is None
    client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=False)
    current = url
    try:
        for _hop in range(MAX_REDIRECTS + 1):
            ensure_public_http_url(current)
            with client.stream("GET", current, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain,*/*"}) as response:
                if response.status_code in _REDIRECTS:
                    location = response.headers.get("location")
                    if not location:
                        raise FetchError("Redirect was missing a Location header")
                    current = urljoin(str(response.url), location)
                    continue
                if response.status_code >= 400:
                    raise FetchError(f"Fetch failed with status {response.status_code}")
                buf = bytearray()
                for chunk in response.iter_bytes():
                    buf.extend(chunk)
                    if len(buf) > MAX_BYTES:
                        raise FetchError("Response exceeds 2 MB")
                return bytes(buf), str(response.url)
        raise FetchError("Too many redirects")
    finally:
        if owns_client:
            client.close()


def rethrow_ssrf(exc: Exception) -> None:
    if isinstance(exc, SSRFError):
        raise exc
