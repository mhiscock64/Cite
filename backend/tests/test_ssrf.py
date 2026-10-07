"""Private, loopback, and link-local URLs are rejected before any request."""

import httpx
import pytest

from app.services.fetch_url import fetch_public_url
from app.services.ssrf import SSRFError, ensure_public_http_url
from tests.helpers import register

BLOCKED = [
    "http://127.0.0.1/secret",
    "http://127.0.0.1:9/secret",
    "http://10.1.2.3/latest",
    "http://192.168.1.20/admin",
    "http://172.16.0.4/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/secret",
    "http://localhost/admin",
    "http://0.0.0.0/",
    "http://2130706433/",
    "http://127.1/",
    "file:///etc/passwd",
]


@pytest.mark.parametrize("url", BLOCKED)
def test_blocked_urls_never_reach_the_client(url):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise AssertionError(f"fetched {request.url}")

    with pytest.raises(SSRFError):
        ensure_public_http_url(url)
    with pytest.raises(SSRFError):
        fetch_public_url(url, client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert calls["n"] == 0


def test_redirect_to_loopback_is_not_followed(monkeypatch):
    import socket

    def fake_getaddrinfo(host, *_args, **_kwargs):
        if host == "example.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]
        raise socket.gaierror(host)

    monkeypatch.setattr("app.services.ssrf.socket.getaddrinfo", fake_getaddrinfo)
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"Location": "http://127.0.0.1/secret"})
        return httpx.Response(200, content=b"nope")

    with pytest.raises(SSRFError):
        fetch_public_url(
            "http://example.com/start",
            client=httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False),
        )
    assert seen == ["http://example.com/start"]


def test_api_rejects_private_url_without_a_document(client, monkeypatch):
    register(client)

    def explode(*_args, **_kwargs):
        raise AssertionError("HTTP client should not be constructed for a blocked URL")

    monkeypatch.setattr("app.services.fetch_url.httpx.Client", explode)
    response = client.post("/documents", json={"source_type": "url", "url": "http://169.254.169.254/latest/meta-data/"})
    assert response.status_code == 400
    assert client.get("/documents").json() == []
