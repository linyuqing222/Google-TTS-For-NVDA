from __future__ import annotations

import ctypes
import threading
from dataclasses import dataclass
from pathlib import Path

try:
    from logHandler import log
except Exception:  # pragma: no cover - NVDA is not available in local unit checks.
    log = None


_DLL_DIR = Path(__file__).with_name("cld2")
_DLL_NAMES = ("cld2_x64.dll", "cld2.dll") if ctypes.sizeof(ctypes.c_void_p) == 8 else ("cld2_x86.dll", "cld2.dll")
_MIN_RELIABLE_PERCENT = 50
_LANGUAGE_ALIASES = {
    "ar": {"ar-xa"},
    "ar-xa": {"ar"},
    "cmn": {"zh"},
    "cmn-cn": {"zh-cn", "zh-hans"},
    "cmn-tw": {"zh-hant", "zh-tw"},
    "fil": {"tl", "fil-ph"},
    "fil-ph": {"fil", "tl"},
    "he": {"iw", "he-il"},
    "he-il": {"he", "iw"},
    "iw": {"he", "he-il"},
    "jv": {"jw", "jv-id"},
    "jv-id": {"jv", "jw"},
    "jw": {"jv", "jv-id"},
    "nb": {"no", "nn", "nb-no"},
    "nb-no": {"nb", "no", "nn"},
    "nn": {"nb", "nb-no", "no"},
    "no": {"nb", "nb-no", "nn"},
    "tl": {"fil", "fil-ph"},
    "yue": {"yue-hk"},
    "yue-hk": {"yue", "zh-hant", "zh-hk"},
    "zh": {"cmn-cn", "cmn-tw", "yue-hk"},
    "zh-cn": {"cmn-cn", "zh-hans"},
    "zh-hans": {"cmn-cn", "zh-cn"},
    "zh-hant": {"cmn-tw", "yue-hk", "zh-hk", "zh-tw"},
    "zh-hk": {"yue-hk", "zh-hant"},
    "zh-tw": {"cmn-tw", "zh-hant"},
}
_CHINESE_LANGUAGE_ROOTS = {"cmn", "yue", "zh"}
# Specific dialect → best supported dialect redirects.
# Modeled after Google TTS APK's LanguageRegistry.nativeGetRedirectForLanguage().
# Only dialects that are commonly requested but not always available need entries.
_LANGUAGE_REDIRECTS: dict[str, str] = {
    "fr-ca": "fr-fr",
    "fr-be": "fr-fr",
    "fr-ch": "fr-fr",
    "fr-lu": "fr-fr",
    "fr-mc": "fr-fr",
    "pt-pt": "pt-br",
    "pt-ao": "pt-br",
    "pt-mz": "pt-br",
    "es-es": "es-mx",
    "es-ar": "es-mx",
    "es-co": "es-mx",
    "es-cl": "es-mx",
    "es-ve": "es-mx",
    "es-pe": "es-mx",
    "es-ec": "es-mx",
    "de-at": "de-de",
    "de-ch": "de-de",
    "en-gb": "en-us",
    "en-au": "en-us",
    "en-in": "en-us",
    "en-za": "en-us",
    "en-nz": "en-us",
    "it-ch": "it-it",
}


def redirect_language(language: str | None, available_languages: set[str]) -> str | None:
    """Redirect an unsupported locale to the best available alternative.

    Modeled after Google TTS APK's LanguageRegistry: when a specific locale
    is not available, return the most appropriate supported locale.
    Returns None if no redirect is needed (language is already available)
    or no suitable redirect exists.
    """
    if not language:
        return None
    key = language.strip().replace("_", "-").lower()
    if key in available_languages:
        return None
    # Check explicit redirects first.
    redirect = _LANGUAGE_REDIRECTS.get(key)
    if redirect and redirect in available_languages:
        return redirect
    # Try root language match (e.g., fr-CA → fr-FR).
    root = key.split("-", 1)[0]
    for available in available_languages:
        if available.split("-", 1)[0] == root:
            return available
    return None


@dataclass(frozen=True)
class DetectionResult:
    language: str
    percent: int
    textBytes: int
    isReliable: bool


class _Cld2Detector:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._library: ctypes.CDLL | None = None
        self._loadAttempted = False
        self._loadErrorLogged = False

    def detect(self, text: str) -> DetectionResult | None:
        if not text:
            return None
        library = self._load_library()
        if library is None:
            return None
        encodedText = text.encode("utf-8", "replace")
        if not encodedText:
            return None
        languageCode = ctypes.create_string_buffer(16)
        percent = ctypes.c_int()
        textBytes = ctypes.c_int()
        isReliable = ctypes.c_int()
        try:
            result = library.cld2_detect_language(
                encodedText,
                len(encodedText),
                languageCode,
                len(languageCode),
                ctypes.byref(percent),
                ctypes.byref(textBytes),
                ctypes.byref(isReliable),
            )
        except Exception:
            if log is not None:
                log.debug("Could not detect language with CLD2.", exc_info=True)
            return None
        if not result:
            return None
        language = languageCode.value.decode("ascii", "replace").strip()
        if not language:
            return None
        return DetectionResult(
            language=language,
            percent=max(0, min(100, int(percent.value))),
            textBytes=max(0, int(textBytes.value)),
            isReliable=bool(isReliable.value),
        )

    def _load_library(self) -> ctypes.CDLL | None:
        with self._lock:
            if self._library is not None:
                return self._library
            if self._loadAttempted:
                return None
            self._loadAttempted = True
            try:
                for dllName in _DLL_NAMES:
                    dllPath = _DLL_DIR / dllName
                    try:
                        library = ctypes.CDLL(str(dllPath))
                        library.cld2_detect_language.argtypes = [
                            ctypes.c_char_p,
                            ctypes.c_int,
                            ctypes.c_char_p,
                            ctypes.c_int,
                            ctypes.POINTER(ctypes.c_int),
                            ctypes.POINTER(ctypes.c_int),
                            ctypes.POINTER(ctypes.c_int),
                        ]
                        library.cld2_detect_language.restype = ctypes.c_int
                        self._library = library
                        return self._library
                    except Exception:
                        if log is not None and not self._loadErrorLogged:
                            log.debug("Could not load CLD2 language detector from %s.", dllPath, exc_info=True)
                return None
            finally:
                if self._library is None:
                    self._loadErrorLogged = True


_detector = _Cld2Detector()


def detect_language(text: str, candidateLanguages: list[str]) -> str | None:
    result = _detector.detect(text)
    if result is None:
        return None
    if not result.isReliable or result.percent < _MIN_RELIABLE_PERCENT:
        return None
    return _candidate_for_language(result.language, candidateLanguages)


def _candidate_for_language(language: str, candidateLanguages: list[str]) -> str | None:
    languageKey = _normalize_language(language)
    if not languageKey:
        return None
    for candidate in candidateLanguages:
        if _normalize_language(candidate) == languageKey:
            return candidate
    languageAliases = _language_aliases(languageKey)
    for candidate in candidateLanguages:
        if _normalize_language(candidate) in languageAliases:
            return candidate
    languageRoot = _language_root(languageKey)
    for candidate in candidateLanguages:
        if _language_root(candidate) == languageRoot:
            return candidate
    if _language_family(languageKey) == "zh":
        for candidate in candidateLanguages:
            if _language_family(candidate) == "zh":
                return candidate
    return None


def language_match_keys(language: str | None) -> set[str]:
    languageKey = _normalize_language(language)
    if not languageKey:
        return set()
    aliases = {languageKey}
    aliases.update(_language_aliases(languageKey))
    root = _language_root(languageKey)
    aliases.add(root)
    aliases.update(_language_aliases(root))
    if _language_family(languageKey) == "zh":
        aliases.update(_CHINESE_LANGUAGE_ROOTS)
    return aliases


def _language_aliases(languageKey: str) -> set[str]:
    return set(_LANGUAGE_ALIASES.get(languageKey, set()))


def _language_family(language: str | None) -> str:
    root = _language_root(language)
    if root in _CHINESE_LANGUAGE_ROOTS:
        return "zh"
    return root


def _language_root(language: str | None) -> str:
    return _normalize_language(language).split("-", 1)[0]


def _normalize_language(language: str | None) -> str:
    return str(language or "").strip().replace("_", "-").lower()


def language_matches(left: str | None, right: str | None) -> bool:
    """Return True when two language tags refer to the same language.

    Uses aliases, root-language matching, and Chinese-family merging so that
    regional variants (fr-FR, fr-CA) and CLDR aliases (fil, tl) are recognised
    as the same language when appropriate.
    """
    leftKeys = language_match_keys(left)
    rightKeys = language_match_keys(right)
    return bool(leftKeys and rightKeys and leftKeys.intersection(rightKeys))
