"""DNS-pinned bounded fetcher for explicitly authorized public URLs."""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from fastapi import HTTPException


def _public_address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    address = ipaddress.ip_address(value)
    if not address.is_global or any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    ):
        raise HTTPException(status_code=422, detail="URL resolves to a non-public network")
    return address


def validate_public_url(url: str) -> tuple[str, tuple[str, ...]]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=422, detail="only HTTP and HTTPS URLs are supported")
    if not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="URL authority is not supported")
    if parsed.port not in {None, 80, 443}:
        raise HTTPException(status_code=422, detail="URL port is not permitted")
    try:
        records = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise HTTPException(status_code=422, detail="URL hostname could not be resolved") from exc
    addresses = tuple(sorted({str(_public_address(str(record[4][0]))) for record in records}))
    if not addresses:
        raise HTTPException(status_code=422, detail="URL has no public address")
    return parsed.hostname, addresses


@dataclass(frozen=True, slots=True)
class FetchResult:
    final_url: str
    content_type: str
    body: bytes


class _ImageParser(HTMLParser):
    """Collect candidate image URLs: social preview images first, then page images."""

    def __init__(self, base_url: str, maximum: int) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.maximum = maximum
        self.urls: list[str] = []

    def _add(self, source: str | None) -> None:
        if not source or len(self.urls) >= self.maximum:
            return
        candidate = urljoin(self.base_url, source.strip())
        if urlsplit(candidate).scheme in {"http", "https"} and candidate not in self.urls:
            self.urls.append(candidate)

    @staticmethod
    def _largest_srcset(value: str | None) -> str | None:
        best: tuple[float, str] | None = None
        for entry in (value or "").split(","):
            parts = entry.strip().split()
            if not parts:
                continue
            size = 1.0
            if len(parts) > 1 and parts[1][:-1].replace(".", "", 1).isdigit():
                size = float(parts[1][:-1])
            if best is None or size > best[0]:
                best = (size, parts[0])
        return best[1] if best else None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        name = tag.casefold()
        if name == "meta":
            key = (values.get("property") or values.get("name") or "").casefold()
            if key in {"og:image", "og:image:url", "og:image:secure_url", "twitter:image"}:
                self._add(values.get("content"))
        elif name == "img":
            self._add(self._largest_srcset(values.get("srcset")) or values.get("data-src") or values.get("src"))


class SafeFetcher:
    def __init__(
        self,
        *,
        timeout: float = 12.0,
        max_bytes: int = 10 * 1024 * 1024,
        max_redirects: int = 3,
        max_candidates: int = 30,
    ) -> None:
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.max_candidates = max_candidates

    def _request_once(self, url: str) -> tuple[int, dict[str, str], bytes]:
        parsed = urlsplit(url)
        host, addresses = validate_public_url(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        last_error: BaseException | None = None
        for address in addresses:
            raw: socket.socket | None = None
            connection: socket.socket | None = None
            try:
                raw = socket.create_connection((address, port), timeout=self.timeout)
                _public_address(raw.getpeername()[0])
                if parsed.scheme == "https":
                    connection = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
                else:
                    connection = raw
                target = parsed.path or "/"
                if parsed.query:
                    target += "?" + parsed.query
                request = (
                    f"GET {target} HTTP/1.1\r\nHost: {host}\r\n"
                    "User-Agent: TraceMark/0.3 link-check (+user-requested)\r\n"
                    "Accept: image/jpeg,image/png,image/webp,text/html;q=0.8\r\n"
                    "Connection: close\r\n\r\n"
                )
                if connection is None:
                    raise OSError("connection was not established")
                connection.sendall(request.encode("ascii"))
                response = http.client.HTTPResponse(connection)
                response.begin()
                headers = {key.casefold(): value for key, value in response.getheaders()}
                declared = headers.get("content-length")
                if declared and int(declared) > self.max_bytes:
                    raise HTTPException(status_code=422, detail="remote response is too large")
                body = response.read(self.max_bytes + 1)
                if len(body) > self.max_bytes:
                    raise HTTPException(status_code=422, detail="remote response is too large")
                return response.status, headers, body
            except HTTPException:
                raise
            except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
                last_error = exc
            finally:
                if connection is not None:
                    connection.close()
                elif raw is not None:
                    raw.close()
        raise HTTPException(status_code=422, detail="public source could not be retrieved") from last_error

    def fetch(self, url: str) -> FetchResult:
        current = url
        for redirect in range(self.max_redirects + 1):
            status, headers, body = self._request_once(current)
            if status in {301, 302, 303, 307, 308}:
                if redirect >= self.max_redirects:
                    raise HTTPException(status_code=422, detail="remote source redirected too many times")
                location = headers.get("location")
                if not location:
                    raise HTTPException(status_code=422, detail="redirect response has no location")
                current = urljoin(current, location)
                validate_public_url(current)
                continue
            if status < 200 or status >= 300:
                raise HTTPException(status_code=422, detail=f"remote source returned HTTP {status}")
            content_type = headers.get("content-type", "").split(";", 1)[0].strip().casefold()
            return FetchResult(current, content_type, body)
        raise HTTPException(status_code=422, detail="remote source could not be retrieved")

    def fetch_image(self, url: str) -> FetchResult:
        result = self.fetch(url)
        if result.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=422, detail="direct URL did not return a supported image")
        return result

    def page_image_urls(self, result: FetchResult) -> list[str]:
        if result.content_type not in {"text/html", "application/xhtml+xml"}:
            raise HTTPException(status_code=422, detail="URL did not return a web page or a supported image")
        parser = _ImageParser(result.final_url, self.max_candidates)
        parser.feed(result.body.decode("utf-8", errors="replace"))
        return parser.urls

    def extract_page_images(self, url: str) -> tuple[FetchResult, list[str]]:
        result = self.fetch(url)
        return result, self.page_image_urls(result)
