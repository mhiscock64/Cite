"""Block fetches to private, loopback, and link-local addresses.

The check runs before the first request and again on every redirect. A host
is rejected when any resolved address is non-public, so a name that mixes a
public address with a private one is still blocked.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse

BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
}


class SSRFError(ValueError):
    """The URL must not be fetched."""


def ensure_public_http_url(url: str) -> None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise SSRFError("Only http and https URLs are allowed")
    host = parsed.hostname
    if not host:
        raise SSRFError("URL is missing a host")
    lowered = host.lower().rstrip(".")
    if (
        lowered in BLOCKED_HOSTS
        or lowered.endswith(".localhost")
        or lowered.endswith(".local")
        or lowered.endswith(".internal")
    ):
        raise SSRFError("URL host is not allowed")
    literal = _literal_ip(lowered)
    if literal is not None:
        if _blocked(literal):
            raise SSRFError("URL points at a private, loopback, or link-local address")
        return
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(lowered, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SSRFError("Could not resolve host") from exc
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        try:
            addresses.append(ipaddress.ip_address(info[4][0]))
        except ValueError:
            continue
    if not addresses:
        raise SSRFError("Could not resolve host")
    if any(_blocked(ip) for ip in addresses):
        raise SSRFError("URL points at a private, loopback, or link-local address")


def _literal_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    if host.startswith("0x") and re.fullmatch(r"0x[0-9a-f]+", host):
        number = int(host, 16)
        if 0 <= number <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(number)
    if re.fullmatch(r"\d{1,10}", host):
        number = int(host)
        if 0 <= number <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(number)
        return None
    parts = host.split(".")
    if not 2 <= len(parts) <= 4 or not all(part.isdigit() for part in parts):
        return None
    nums = [int(part) for part in parts]
    if any(num < 0 or num > 0xFFFFFF for num in nums):
        return None
    try:
        if len(parts) == 4:
            if any(num > 255 for num in nums):
                return None
            return ipaddress.IPv4Address(".".join(str(num) for num in nums))
        if len(parts) == 3:
            return ipaddress.IPv4Address((nums[0] << 24) | (nums[1] << 16) | nums[2])
        return ipaddress.IPv4Address((nums[0] << 24) | nums[1])
    except ValueError:
        return None


def _blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return _blocked(ip.ipv4_mapped)
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )
