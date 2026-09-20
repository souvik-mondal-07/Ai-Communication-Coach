"""
Deterministic text-analysis helpers.

Pure functions (no I/O, no AI) used by the speaking analysis in
`app.services.communication.analysis_service`: tokenising, sentence
splitting, filler-word detection and repetition detection.

Everything here is a *heuristic*. Filler-word detection in particular is
English-oriented and deliberately conservative for words that are often
legitimate ("like", "so", "you know", "I mean") — those only count when the
surrounding words/punctuation suggest they're being used as filler.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

# A token is a word (letters/digits, optionally with internal apostrophes or
# hyphens, e.g. "don't", "well-known") or a single punctuation mark.
_TOKEN_RE = re.compile(r"[^\W_]+(?:['\u2019\-][^\W_]+)*|[,.;:!?\u2026]")

_SENTENCE_END = frozenset({".", "!", "?", "\u2026"})
_PUNCTUATION = frozenset({",", ";", ":"}) | _SENTENCE_END

# --- Filler words -----------------------------------------------------------

# Non-lexical hesitation sounds: always a filler.
_HESITATIONS = frozenset({"um", "umm", "uhm", "uh", "uhh", "er", "erm", "hmm"})

# The built-in list. Order is irrelevant; multi-word phrases are matched as
# consecutive words. Configurable via `FILLER_WORDS` / the `filler_words`
# argument — see `detect_filler_words`.
DEFAULT_FILLER_WORDS: tuple[str, ...] = (
    "um",
    "uh",
    "er",
    "erm",
    "hmm",
    "like",
    "actually",
    "basically",
    "you know",
    "i mean",
    "so",
)

# Words that make a following "like" a comparison / verb rather than a filler.
_LIKE_FOLLOWERS_LEGIT = frozenset(
    {
        "a", "an", "the", "this", "that", "these", "those", "my", "your", "his",
        "her", "our", "their", "its", "to", "it", "you", "me", "him", "them",
        "us", "someone", "somebody", "when",
    }
)
# Words after which "like ..." is very often a filler ("it was like really hard").
_LIKE_FILLER_PRECEDERS = frozenset(
    {
        "was", "is", "were", "are", "am", "it's", "that's", "he's", "she's",
        "i'm", "they're", "we're", "you're", "and", "but", "so", "then",
        "because",
    }
)
_YOU_KNOW_EXCLUDED_PREV = frozenset(
    {"do", "did", "does", "don't", "didn't", "if", "as", "what", "how", "that", "when", "who"}
)
_YOU_KNOW_EXCLUDED_NEXT = frozenset(
    {
        "what", "how", "why", "when", "where", "who", "whether", "that", "if",
        "the", "a", "an", "this", "my", "your", "about", "it", "him", "her", "them",
    }
)
_I_MEAN_EXCLUDED_PREV = frozenset({"what", "if", "do", "did", "when", "as", "that"})


def _prev(tokens: list[str], start: int) -> str | None:
    return tokens[start - 1] if start > 0 else None


def _next(tokens: list[str], end: int) -> str | None:
    return tokens[end] if end < len(tokens) else None


def _like_is_filler(tokens: list[str], start: int, end: int) -> bool:
    prev, nxt = _prev(tokens, start), _next(tokens, end)
    # "I was, like, nervous" / "Like, I don't know" — set off by commas.
    if prev == "," or nxt == ",":
        return True
    # "like a professional", "like this" — a comparison, not a filler.
    if nxt in _LIKE_FOLLOWERS_LEGIT:
        return False
    # "it was like really hard", "and like I said".
    if prev in _LIKE_FILLER_PRECEDERS and nxt is not None and nxt not in _PUNCTUATION:
        return True
    # "I like cybersecurity", "something like this", "would like to" ...
    return False


def _so_is_filler(tokens: list[str], start: int, end: int) -> bool:
    prev, nxt = _prev(tokens, start), _next(tokens, end)
    clause_start = prev is None or prev in _SENTENCE_END or prev == "," or prev in {"and", "but"}
    # "So, yeah, ..." — but not "I think so, but ..." (prev isn't a clause start).
    if nxt == "," and clause_start:
        return True
    # "so um ..."
    return nxt in _HESITATIONS


def _you_know_is_filler(tokens: list[str], start: int, end: int) -> bool:
    prev, nxt = _prev(tokens, start), _next(tokens, end)
    if prev in _YOU_KNOW_EXCLUDED_PREV or nxt in _YOU_KNOW_EXCLUDED_NEXT:
        return False  # "Do you know how...", "as you know, ...", "you know it"
    return prev == "," or nxt == "," or nxt is None or nxt in _SENTENCE_END


def _i_mean_is_filler(tokens: list[str], start: int, end: int) -> bool:
    prev, nxt = _prev(tokens, start), _next(tokens, end)
    if prev in _I_MEAN_EXCLUDED_PREV:
        return False  # "What I mean is..."
    # "I mean, it's fine." — a discourse marker set off by a comma.
    return nxt == "," or (prev == "," and (nxt is None or nxt in _SENTENCE_END))


# phrase -> predicate(tokens, start, end). Anything not listed here counts
# unconditionally every time it appears (hesitations, "basically", "actually",
# and any custom word the user configures).
_CONTEXTUAL_RULES = {
    "like": _like_is_filler,
    "so": _so_is_filler,
    "you know": _you_know_is_filler,
    "i mean": _i_mean_is_filler,
}


# --- Tokenising & counting --------------------------------------------------


def tokenize(text: str) -> list[str]:
    """Lower-cased word and punctuation tokens (curly apostrophes normalised)."""
    normalised = text.replace("\u2019", "'")
    return [t.lower() for t in _TOKEN_RE.findall(normalised)]


def _words(tokens: Iterable[str]) -> list[str]:
    return [t for t in tokens if t not in _PUNCTUATION]


def count_words(text: str) -> int:
    return len(_words(tokenize(text)))


def count_sentences(text: str) -> int:
    """Sentences by terminal punctuation; unpunctuated text counts as one."""
    stripped = text.strip()
    if not stripped:
        return 0
    parts = re.split(r"(?<=[.!?\u2026])\s+", stripped)
    return sum(1 for part in parts if _words(tokenize(part)))


def _normalise_phrase(phrase: str) -> list[str]:
    return [t for t in tokenize(phrase) if t not in _PUNCTUATION]


def detect_filler_words(
    text: str, filler_words: Iterable[str] | None = None
) -> tuple[dict[str, int], int]:
    """
    Count filler words in `text`.

    `filler_words` is the (configurable) list of phrases to look for; None
    uses `DEFAULT_FILLER_WORDS`. "like", "so", "you know" and "I mean" are
    only counted when context suggests filler use (see rules above).

    Returns `({"um": 3, "basically": 2}, total)`.
    """
    phrases = list(filler_words) if filler_words is not None else list(DEFAULT_FILLER_WORDS)
    tokens = tokenize(text)

    # Longest phrases first so "you know" wins over a hypothetical "know".
    normalised = sorted(
        {" ".join(p): p for p in (_normalise_phrase(x) for x in phrases) if p}.items(),
        key=lambda item: -len(item[1]),
    )

    counts: Counter[str] = Counter()
    consumed: set[int] = set()
    for key, phrase_tokens in normalised:
        size = len(phrase_tokens)
        rule = _CONTEXTUAL_RULES.get(key)
        for i in range(len(tokens) - size + 1):
            if tokens[i : i + size] != phrase_tokens:
                continue
            span = set(range(i, i + size))
            if span & consumed:
                continue
            if rule is not None and not rule(tokens, i, i + size):
                continue
            counts[key] += 1
            consumed |= span

    result = dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    return result, sum(result.values())


# --- Repetition -------------------------------------------------------------

# Legitimate doubled words ("he had had enough").
_LEGIT_REPEATS = frozenset({"had"})

_STOPWORDS = frozenset(
    """
    that this with have from they will would there their what about which when
    your just like really think very been were them then than some also into
    more could should because where actually basically know want going thing
    things people make made much many well even still back only over such
    while being those these here other after before every another
    """.split()
)


def find_repeated_words(text: str) -> tuple[dict[str, int], int]:
    """
    Immediate repetitions ("the the", "I, I think") — a common speech
    disfluency. Returns `({"the": 1}, total)`.
    """
    tokens = tokenize(text)
    counts: Counter[str] = Counter()
    i = 0
    while i < len(tokens) - 1:
        cur = tokens[i]
        if cur in _PUNCTUATION or cur in _LEGIT_REPEATS:
            i += 1
            continue
        # "the the" or "I, I"
        j = i + 1
        if j < len(tokens) and tokens[j] == ",":
            j += 1
        if j < len(tokens) and tokens[j] == cur:
            counts[cur] += 1
            i = j  # keep scanning from the repeat so "the the the" counts twice
            continue
        i += 1
    result = dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    return result, sum(result.values())


def find_overused_words(
    text: str, *, min_words: int = 25, min_count: int = 3, limit: int = 5
) -> dict[str, int]:
    """
    Content words used many times in a short stretch — "unnecessary
    repetition" of the same point. Ignores stopwords and short words, and
    only fires once there's enough text for repetition to be meaningful.
    """
    words = _words(tokenize(text))
    if len(words) < min_words:
        return {}
    counts = Counter(w for w in words if len(w) >= 4 and w not in _STOPWORDS and not w.isdigit())
    over = [(w, c) for w, c in counts.items() if c >= min_count]
    over.sort(key=lambda kv: (-kv[1], kv[0]))
    return dict(over[:limit])


def lexical_diversity(text: str) -> float | None:
    """Unique words / total words (type-token ratio), or None for empty text."""
    words = _words(tokenize(text))
    if not words:
        return None
    return len(set(words)) / len(words)
