from __future__ import annotations

import unittest

from tests.test_support import load_driver_module

language_utils = load_driver_module("language_utils")


class LanguageUtilsTests(unittest.TestCase):
    def test_normalize_language(self) -> None:
        self.assertEqual(language_utils.normalize_language("en_US"), "en-us")
        self.assertEqual(language_utils.normalize_language("vi-VN"), "vi-vn")
        self.assertEqual(language_utils.normalize_language("  ZH_cn  "), "zh-cn")
        self.assertEqual(language_utils.normalize_language(None), "")

    def test_normalize_language_code(self) -> None:
        self.assertEqual(language_utils.normalize_language_code("en_US"), "en-US")
        self.assertEqual(language_utils.normalize_language_code("vi-VN"), "vi-VN")
        self.assertEqual(language_utils.normalize_language_code(None), "")

    def test_get_nvda_locale_special_cases(self) -> None:
        self.assertEqual(language_utils.get_nvda_locale_for_language("cmn-CN"), "zh_CN")
        self.assertEqual(language_utils.get_nvda_locale_for_language("cmn-TW"), "zh_TW")
        self.assertEqual(language_utils.get_nvda_locale_for_language("yue-HK"), "zh_HK")
        self.assertEqual(language_utils.get_nvda_locale_for_language("ar-XA"), "ar")
        self.assertEqual(language_utils.get_nvda_locale_for_language("fil-PH"), "tl")

    def test_get_nvda_locale_prefixes(self) -> None:
        self.assertEqual(language_utils.get_nvda_locale_for_language("cmn-Hans-CN"), "zh_CN")
        self.assertEqual(language_utils.get_nvda_locale_for_language("yue-Hant-HK"), "zh_HK")

    def test_resolve_nvda_locale_fallback_to_en(self) -> None:
        self.assertEqual(language_utils.resolve_nvda_locale(None), "en")
        self.assertEqual(language_utils.resolve_nvda_locale(""), "en")

    def test_get_language_display_name_with_custom_dict(self) -> None:
        custom_names = {"vi-VN": "Tiếng Việt", "en-US": "English (US)"}
        self.assertEqual(language_utils.get_language_display_name("vi-VN", custom_names), "Tiếng Việt")
        self.assertEqual(language_utils.get_language_display_name("en_us", custom_names), "English (US)")
        self.assertEqual(language_utils.get_language_display_name("fr-FR", custom_names), "fr-FR")


if __name__ == "__main__":
    unittest.main()
