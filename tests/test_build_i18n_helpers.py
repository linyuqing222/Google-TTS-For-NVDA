"""Tests for pure helper functions in build_i18n.py.

Covers PO file parsing, MO compilation, language code normalization,
string formatting utilities, and manifest value extraction.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import build_i18n

# ---------------------------------------------------------------------------
# _parse_po
# ---------------------------------------------------------------------------


class ParsePoTests(unittest.TestCase):
    """Verify PO file parsing handles standard and edge-case files."""

    def _write_po(self, tmpdir: Path, content: str) -> Path:
        po_path = tmpdir / "test.po"
        po_path.write_text(content, encoding="utf-8")
        return po_path

    def test_simple_po(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            po_path = self._write_po(
                Path(td),
                'msgid ""\nmsgstr ""\n\nmsgid "Hello"\nmsgstr "Привіт"\n',
            )
            catalog = build_i18n._parse_po(po_path)
            self.assertIn("Hello", catalog)
            self.assertTrue(catalog["Hello"])

    def test_multiline_msgstr(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            po_path = self._write_po(
                Path(td),
                'msgid ""\nmsgstr ""\n\nmsgid "Multi"\nmsgstr ""\n"line1\\n"\n"line2"\n',
            )
            catalog = build_i18n._parse_po(po_path)
            self.assertEqual("line1\nline2", catalog["Multi"])

    def test_empty_msgstr_not_included(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            po_path = self._write_po(
                Path(td),
                'msgid ""\nmsgstr ""\n\nmsgid "Untranslated"\nmsgstr ""\n',
            )
            catalog = build_i18n._parse_po(po_path)
            self.assertNotIn("Untranslated", catalog)

    def test_include_untranslated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            po_path = self._write_po(
                Path(td),
                'msgid ""\nmsgstr ""\n\nmsgid "Untranslated"\nmsgstr ""\n',
            )
            catalog = build_i18n._parse_po(po_path, include_untranslated=True)
            self.assertIn("Untranslated", catalog)

    def test_msgctxt_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            po_path = self._write_po(
                Path(td),
                'msgid ""\nmsgstr ""\n\nmsgctxt "ctx"\nmsgid "Key"\nmsgstr "Val"\n',
            )
            catalog = build_i18n._parse_po(po_path)
            self.assertEqual("Val", catalog["Key"])


# ---------------------------------------------------------------------------
# _format_set
# ---------------------------------------------------------------------------


class FormatSetTests(unittest.TestCase):
    """Verify _format_set extracts placeholders from format strings."""

    def test_python_brace_placeholders(self) -> None:
        result = build_i18n._format_set("Hello {name}, you have {count} items")
        self.assertEqual({"{name}", "{count}"}, result)

    def test_no_placeholders(self) -> None:
        result = build_i18n._format_set("No placeholders here")
        self.assertEqual(set(), result)

    def test_empty_string(self) -> None:
        result = build_i18n._format_set("")
        self.assertEqual(set(), result)

    def test_repeated_placeholder(self) -> None:
        result = build_i18n._format_set("{x} and {x}")
        self.assertEqual({"{x}"}, result)


# ---------------------------------------------------------------------------
# _normalize_language_code
# ---------------------------------------------------------------------------


class NormalizeLanguageCodeTests(unittest.TestCase):
    """Verify _normalize_language_code normalizes language codes."""

    def test_simple_code(self) -> None:
        self.assertEqual("en", build_i18n._normalize_language_code("en"))

    def test_locale_with_dash(self) -> None:
        self.assertEqual("en_US", build_i18n._normalize_language_code("en-us"))

    def test_locale_with_underscore(self) -> None:
        self.assertEqual("en_US", build_i18n._normalize_language_code("en_US"))

    def test_whitespace_trimmed(self) -> None:
        self.assertEqual("fr_FR", build_i18n._normalize_language_code("  fr-fr  "))

    def test_empty_string(self) -> None:
        self.assertEqual("", build_i18n._normalize_language_code(""))


# ---------------------------------------------------------------------------
# _po_escape and _po_quoted_lines
# ---------------------------------------------------------------------------


class PoEscapeTests(unittest.TestCase):
    """Verify PO string escaping and quoting."""

    def test_backslash_escaped(self) -> None:
        result = build_i18n._po_escape("path\\to")
        self.assertEqual("path\\\\to", result)

    def test_quote_escaped(self) -> None:
        result = build_i18n._po_escape('say "hello"')
        self.assertEqual('say \\"hello\\"', result)

    def test_newline_escaped(self) -> None:
        result = build_i18n._po_escape("line1\nline2")
        self.assertEqual("line1\\nline2", result)

    def test_tab_escaped(self) -> None:
        result = build_i18n._po_escape("col1\tcol2")
        self.assertEqual("col1\\tcol2", result)

    def test_quoted_lines_single_line(self) -> None:
        result = build_i18n._po_quoted_lines("hello")
        self.assertEqual(['"hello"'], result)

    def test_quoted_lines_empty(self) -> None:
        result = build_i18n._po_quoted_lines("")
        self.assertEqual(['""'], result)


# ---------------------------------------------------------------------------
# _purge_obsolete_po_entries
# ---------------------------------------------------------------------------


class PurgeObsoleteTests(unittest.TestCase):
    """Verify _purge_obsolete_po_entries removes obsolete blocks."""

    def test_removes_obsolete_entries(self) -> None:
        text = (
            '# Header\n\nmsgid ""\nmsgstr "Language: uk\\n"\n\n'
            'msgid "Current"\nmsgstr "Поточний"\n\n'
            '#~ msgid "Old"\n#~ msgstr "Старий"\n'
        )
        updated, removed = build_i18n._purge_obsolete_po_entries(text)
        self.assertEqual(1, removed)
        self.assertIn('msgid "Current"', updated)
        self.assertNotIn("Old", updated)

    def test_no_obsolete(self) -> None:
        text = 'msgid ""\nmsgstr ""\n\nmsgid "Key"\nmsgstr "Val"\n'
        updated, removed = build_i18n._purge_obsolete_po_entries(text)
        self.assertEqual(0, removed)
        self.assertIn('msgid "Key"', updated)


# ---------------------------------------------------------------------------
# _manifest_values
# ---------------------------------------------------------------------------


class ManifestValuesTests(unittest.TestCase):
    """Verify _manifest_values reads triple-quoted fields."""

    def test_reads_summary_and_description(self) -> None:
        values = build_i18n._manifest_values()
        self.assertIn("summary", values)
        self.assertIn("description", values)
        self.assertTrue(values["summary"])
        self.assertTrue(values["description"])


# ---------------------------------------------------------------------------
# _message_preview
# ---------------------------------------------------------------------------


class MessagePreviewTests(unittest.TestCase):
    """Verify _message_preview truncates long messages."""

    def test_short_message(self) -> None:
        result = build_i18n._message_preview("Hello")
        self.assertEqual("Hello", result)

    def test_long_message_truncated(self) -> None:
        result = build_i18n._message_preview("A" * 200, limit=50)
        self.assertEqual(50, len(result))
        self.assertTrue(result.endswith("..."))

    def test_newline_replaced(self) -> None:
        result = build_i18n._message_preview("line1\nline2")
        self.assertIn("\\n", result)
        self.assertNotIn("\n", result)


if __name__ == "__main__":
    unittest.main()
