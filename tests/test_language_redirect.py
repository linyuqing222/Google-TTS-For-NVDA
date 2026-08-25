"""Tests for language redirect and consolidated language matching helpers."""

from __future__ import annotations

import unittest

from tests.test_support import load_driver_module


class LanguageRedirectTests(unittest.TestCase):
    """Verify redirect_language() redirects unsupported locales to the best
    available alternative, matching Google TTS APK's LanguageRegistry."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ld = load_driver_module("language_detector")

    def test_no_redirect_when_language_already_available(self) -> None:
        available = {"en-us", "fr-fr"}
        self.assertIsNone(self.ld.redirect_language("en-us", available))
        self.assertIsNone(self.ld.redirect_language("fr-fr", available))

    def test_no_redirect_for_none_language(self) -> None:
        self.assertIsNone(self.ld.redirect_language(None, {"en-us"}))
        self.assertIsNone(self.ld.redirect_language("", {"en-us"}))

    def test_underscore_is_normalised(self) -> None:
        # "fr_fr" normalises to "fr-fr" which is already available
        available = {"fr-fr"}
        self.assertIsNone(self.ld.redirect_language("fr_fr", available))

    def test_underscore_redirect_when_needed(self) -> None:
        available = {"fr-fr"}
        self.assertEqual("fr-fr", self.ld.redirect_language("fr_ca", available))

    # --- explicit redirect map entries -----------------------------------

    def test_french_canadian_redirects_to_fr_fr(self) -> None:
        available = {"fr-fr"}
        self.assertEqual("fr-fr", self.ld.redirect_language("fr-ca", available))

    def test_portuguese_european_redirects_to_pt_br(self) -> None:
        available = {"pt-br"}
        self.assertEqual("pt-br", self.ld.redirect_language("pt-pt", available))

    def test_spanish_spain_redirects_to_es_mx(self) -> None:
        available = {"es-mx"}
        self.assertEqual("es-mx", self.ld.redirect_language("es-es", available))

    def test_german_austrian_redirects_to_de_de(self) -> None:
        available = {"de-de"}
        self.assertEqual("de-de", self.ld.redirect_language("de-at", available))

    def test_german_swiss_redirects_to_de_de(self) -> None:
        available = {"de-de"}
        self.assertEqual("de-de", self.ld.redirect_language("de-ch", available))

    def test_english_gb_redirects_to_en_us(self) -> None:
        available = {"en-us"}
        self.assertEqual("en-us", self.ld.redirect_language("en-gb", available))

    def test_english_australian_redirects_to_en_us(self) -> None:
        available = {"en-us"}
        self.assertEqual("en-us", self.ld.redirect_language("en-au", available))

    def test_italian_swiss_redirects_to_it_it(self) -> None:
        available = {"it-it"}
        self.assertEqual("it-it", self.ld.redirect_language("it-ch", available))

    def test_redirect_prefers_explicit_over_root(self) -> None:
        """Explicit redirect should win over a generic root match."""
        available = {"fr-fr", "fr-ca"}
        # fr-ca is in available, so no redirect needed
        self.assertIsNone(self.ld.redirect_language("fr-ca", available))

    # --- root-language fallback -----------------------------------------

    def test_root_language_fallback_when_no_explicit_redirect(self) -> None:
        """A dialect without an explicit redirect should fall back to any
        available dialect of the same root language."""
        available = {"ko-kr"}
        self.assertEqual("ko-kr", self.ld.redirect_language("ko-kp", available))

    def test_root_fallback_returns_first_available(self) -> None:
        available = {"ja-jp", "ja"}
        result = self.ld.redirect_language("ja-xx", available)
        self.assertIn(result, available)

    # --- no redirect possible ------------------------------------------

    def test_no_redirect_when_no_available_language_matches(self) -> None:
        available = {"en-us", "fr-fr"}
        self.assertIsNone(self.ld.redirect_language("xx-xx", available))

    def test_no_redirect_when_available_is_empty(self) -> None:
        self.assertIsNone(self.ld.redirect_language("en-us", set()))


class LanguageMatchesTests(unittest.TestCase):
    """Verify the consolidated language_matches() helper."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ld = load_driver_module("language_detector")

    def test_exact_match(self) -> None:
        self.assertTrue(self.ld.language_matches("en-us", "en-us"))

    def test_root_match(self) -> None:
        self.assertTrue(self.ld.language_matches("fr-fr", "fr-ca"))

    def test_alias_match_fil_tl(self) -> None:
        self.assertTrue(self.ld.language_matches("fil", "tl"))
        self.assertTrue(self.ld.language_matches("fil-ph", "tl"))

    def test_chinese_family_match(self) -> None:
        self.assertTrue(self.ld.language_matches("cmn-cn", "zh-hans"))
        self.assertTrue(self.ld.language_matches("zh", "cmn-tw"))
        self.assertTrue(self.ld.language_matches("yue-hk", "zh-hant"))

    def test_no_match_across_families(self) -> None:
        self.assertFalse(self.ld.language_matches("en-us", "fr-fr"))

    def test_none_returns_false(self) -> None:
        self.assertFalse(self.ld.language_matches(None, "en-us"))
        self.assertFalse(self.ld.language_matches("en-us", None))
        self.assertFalse(self.ld.language_matches(None, None))

    def test_empty_string_returns_false(self) -> None:
        self.assertFalse(self.ld.language_matches("", "en-us"))
        self.assertFalse(self.ld.language_matches("en-us", ""))

    def test_normalisation_underscore(self) -> None:
        self.assertTrue(self.ld.language_matches("en_US", "en-us"))

    def test_hebrew_aliases(self) -> None:
        self.assertTrue(self.ld.language_matches("he", "iw"))
        self.assertTrue(self.ld.language_matches("he-il", "iw"))


if __name__ == "__main__":
    unittest.main()
