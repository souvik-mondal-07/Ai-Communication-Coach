"""Turn untrusted feed text into safe plain text. Feed content is data, never markup."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
_SKIP_TAGS = {"script", "style", "iframe", "object", "embed", "noscript", "template", "svg"}
_BLOCK_TAGS = {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u202a-\u202e\u2066-\u2069]")  # incl. bidi overrides
_WS_RE = re.compile(r"\s+")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data):  # noqa: ANN001
        if not self._skip:
            self.parts.append(data)


def to_plain_text(value: object, *, limit: int | None = None) -> str | None:
    """Strip tags/scripts/entities/control characters, collapse whitespace, truncate on a word."""
    if not isinstance(value, str) or not value.strip():
        return None
    parser = _TextExtractor()
    try:
        parser.feed(value[:20_000])
        parser.close()
    except Exception:  # noqa: BLE001 - malformed markup: fall back to a crude strip
        parser.parts = [re.sub(r"<[^>]*>", " ", value[:20_000])]
    text = html.unescape("".join(parser.parts))
    text = _WS_RE.sub(" ", _CONTROL_RE.sub("", text)).strip()
    if not text:
        return None
    if limit and len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.-–—")
        text = (cut or text[:limit]) + "…"
    return text


def extract_cve_ids(*values: object) -> list[str]:
    """CVE ids that literally appear in the given source-supplied strings (de-duplicated, ordered)."""
    seen: dict[str, None] = {}
    for value in values:
        if isinstance(value, str):
            for match in CVE_RE.findall(value):
                seen.setdefault(match.upper(), None)
    return list(seen)[:10]
