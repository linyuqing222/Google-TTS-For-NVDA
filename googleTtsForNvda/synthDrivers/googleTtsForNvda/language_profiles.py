"""Pure helpers for Unicode-script language-profile fallback.

This module intentionally has no NVDA imports so the same production logic can
be exercised by the standalone test suite.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection

from .unicode_data import LANGUAGE_SCRIPT_RANGES

ScriptRanges = tuple[tuple[int, int], ...]

LANGUAGE_WORD_RE = re.compile(r"[^\W\d_]+(?:['’_-][^\W\d_]+)?", re.UNICODE)
VIETNAMESE_LETTERS = set("ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")
VIETNAMESE_WORDS = {
    "anh",
    "ban",
    "bạn",
    "bao",
    "bi",
    "bị",
    "bo",
    "bỏ",
    "cai",
    "cái",
    "cac",
    "các",
    "can",
    "cần",
    "cau",
    "câu",
    "cho",
    "co",
    "có",
    "con",
    "cua",
    "của",
    "cung",
    "cùng",
    "dang",
    "đang",
    "de",
    "để",
    "den",
    "đến",
    "di",
    "đi",
    "do",
    "đó",
    "duoc",
    "được",
    "hay",
    "hon",
    "hơn",
    "khi",
    "khong",
    "không",
    "la",
    "là",
    "lam",
    "làm",
    "len",
    "lên",
    "mot",
    "một",
    "nay",
    "này",
    "neu",
    "nếu",
    "nguoi",
    "người",
    "nhung",
    "những",
    "o",
    "ở",
    "qua",
    "ra",
    "rang",
    "rằng",
    "roi",
    "rồi",
    "sau",
    "se",
    "sẽ",
    "thi",
    "thì",
    "toi",
    "tôi",
    "trong",
    "tu",
    "từ",
    "va",
    "và",
    "vao",
    "vào",
    "ve",
    "về",
    "vi",
    "vì",
    "voi",
    "với",
}
ENGLISH_WORDS = {
    "a",
    "about",
    "after",
    "all",
    "also",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "between",
    "brave",
    "browser",
    "but",
    "by",
    "can",
    "chrome",
    "click",
    "could",
    "did",
    "do",
    "does",
    "download",
    "edge",
    "for",
    "from",
    "has",
    "have",
    "if",
    "in",
    "install",
    "is",
    "it",
    "language",
    "more",
    "not",
    "of",
    "on",
    "open",
    "or",
    "package",
    "press",
    "runtime",
    "select",
    "settings",
    "speech",
    "than",
    "that",
    "the",
    "then",
    "there",
    "this",
    "to",
    "use",
    "voice",
    "was",
    "were",
    "when",
    "will",
    "with",
    "you",
    "your",
}


def script_ranges_for_language_root(root: str) -> ScriptRanges:
    return LANGUAGE_SCRIPT_RANGES.get(root, ())


def token_has_character_in_ranges(token: str, ranges: ScriptRanges) -> bool:
    return any(start <= ord(character) <= end for character in token for start, end in ranges)


def language_script_signal(token: str, candidateRoots: Collection[str]) -> str | None:
    """Return the only candidate root whose generated script ranges match."""
    matchingRoots = {
        root
        for root in candidateRoots
        if (ranges := script_ranges_for_language_root(root)) and token_has_character_in_ranges(token, ranges)
    }
    if len(matchingRoots) == 1:
        return next(iter(matchingRoots))
    return None


def language_token_signal(
    token: str,
    candidateRoots: Collection[str],
    is_url_token: Callable[[str], bool] | None = None,
) -> tuple[str | None, int]:
    normalized = token.strip("'’_-").casefold()
    if not normalized or (is_url_token is not None and is_url_token(normalized)):
        return None, 0
    scriptRoot = language_script_signal(normalized, candidateRoots)
    if scriptRoot is not None:
        return scriptRoot, 2
    if "vi" in candidateRoots and any(character in VIETNAMESE_LETTERS for character in normalized):
        return "vi", 2
    viScore = 1 if "vi" in candidateRoots and normalized in VIETNAMESE_WORDS else 0
    enScore = 1 if "en" in candidateRoots and normalized in ENGLISH_WORDS else 0
    if viScore > enScore:
        return "vi", viScore
    if enScore > viScore:
        return "en", enScore
    return None, 0
