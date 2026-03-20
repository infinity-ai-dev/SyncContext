from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def connection_kwargs_from_url(url: str) -> dict:
    """Return asyncpg connection kwargs derived from DSN query params."""
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    kwargs = {}
    if params.get("pgbouncer", "").lower() == "true":
        # Prepared statement caching is incompatible with transaction pooling.
        kwargs["statement_cache_size"] = 0
    return kwargs


def redact_database_url(url: str) -> str:
    """Return a DSN safe to log by masking the password."""
    parsed = urlparse(url)
    if parsed.password is None:
        return url

    netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@", 1)
    return urlunparse(parsed._replace(netloc=netloc))


def unique_urls(urls: Iterable[str | None]) -> list[str]:
    """Keep insertion order while dropping empty and duplicate DSNs."""
    seen: set[str] = set()
    result: list[str] = []

    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(url)

    return result
