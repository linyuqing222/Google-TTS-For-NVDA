"""Tests for pure helper functions in generate_unicode_data.py.

Covers UCD record parsing, script alias resolution, range merging,
and module rendering helpers.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import generate_unicode_data

# ---------------------------------------------------------------------------
# _parse_ucd_records
# ---------------------------------------------------------------------------


class ParseUcdRecordsTests(unittest.TestCase):
    """Verify _parse_ucd_records parses UCD semicolon-delimited files."""

    def _write_ucd(self, tmpdir: Path, content: str) -> Path:
        path = tmpdir / "Scripts.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def test_single_codepoint(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = self._write_ucd(Path(td), "# Comment\n0041 ; Lc # Latin\n")
            records = generate_unicode_data._parse_ucd_records(path)
            self.assertEqual([(0x0041, 0x0041, "Lc")], records)

    def test_range(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = self._write_ucd(Path(td), "0041..005A ; L # Latin\n")
            records = generate_unicode_data._parse_ucd_records(path)
            self.assertEqual([(0x0041, 0x005A, "L")], records)

    def test_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = self._write_ucd(Path(td), "# Only comments\n")
            records = generate_unicode_data._parse_ucd_records(path)
            self.assertEqual([], records)

    def test_multiple_records(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = self._write_ucd(
                Path(td),
                "0041..005A ; L # Latin\n0030..0039 ; Nd # Number\n",
            )
            records = generate_unicode_data._parse_ucd_records(path)
            self.assertEqual(2, len(records))


# ---------------------------------------------------------------------------
# _merge_ranges
# ---------------------------------------------------------------------------


class MergeRangesTests(unittest.TestCase):
    """Verify _merge_ranges merges overlapping and adjacent ranges."""

    def test_non_overlapping(self) -> None:
        result = generate_unicode_data._merge_ranges([(1, 5), (10, 15)])
        self.assertEqual(((1, 5), (10, 15)), result)

    def test_overlapping(self) -> None:
        result = generate_unicode_data._merge_ranges([(1, 5), (3, 10)])
        self.assertEqual(((1, 10),), result)

    def test_adjacent(self) -> None:
        result = generate_unicode_data._merge_ranges([(1, 5), (6, 10)])
        self.assertEqual(((1, 10),), result)

    def test_empty_input(self) -> None:
        result = generate_unicode_data._merge_ranges([])
        self.assertEqual((), result)

    def test_single_range(self) -> None:
        result = generate_unicode_data._merge_ranges([(1, 5)])
        self.assertEqual(((1, 5),), result)

    def test_unsorted_input(self) -> None:
        result = generate_unicode_data._merge_ranges([(10, 15), (1, 5)])
        self.assertEqual(((1, 5), (10, 15)), result)

    def test_three_ranges_merge(self) -> None:
        result = generate_unicode_data._merge_ranges([(1, 3), (2, 5), (6, 10)])
        self.assertEqual(((1, 10),), result)


# ---------------------------------------------------------------------------
# _script_aliases
# ---------------------------------------------------------------------------


class ScriptAliasesTests(unittest.TestCase):
    """Verify _script_aliases parses PropertyValueAliases.txt."""

    def _write_aliases(self, tmpdir: Path, content: str) -> Path:
        path = tmpdir / "PropertyValueAliases.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def test_sc_alias(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = self._write_aliases(
                Path(td),
                "# Comment\nsc ; Arab ; Arabic\nsc ; Latn ; Latin\n",
            )
            aliases = generate_unicode_data._script_aliases(path)
            self.assertEqual("Arabic", aliases["Arab"])
            self.assertEqual("Latin", aliases["Latn"])

    def test_hans_hant_always_alias_to_han(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = self._write_aliases(Path(td), "sc ; Arab ; Arabic\n")
            aliases = generate_unicode_data._script_aliases(path)
            self.assertEqual("Han", aliases["Hans"])
            self.assertEqual("Han", aliases["Hant"])


# ---------------------------------------------------------------------------
# _format_ranges
# ---------------------------------------------------------------------------


class FormatRangesTests(unittest.TestCase):
    """Verify _format_ranges renders codepoint ranges as C-style tuples."""

    def test_single_range(self) -> None:
        result = generate_unicode_data._format_ranges([(0x0041, 0x005A)])
        self.assertIn("0x0041", result)
        self.assertIn("0x005A", result)

    def test_multiple_ranges(self) -> None:
        result = generate_unicode_data._format_ranges([(1, 5), (10, 15)])
        self.assertIn("0x0001", result)
        self.assertIn("0x000A", result)


# ---------------------------------------------------------------------------
# _format_codepoints
# ---------------------------------------------------------------------------


class FormatCodepointsTests(unittest.TestCase):
    """Verify _format_codepoints renders sorted hex codepoints."""

    def test_sorted_output(self) -> None:
        result = generate_unicode_data._format_codepoints([0x003F, 0x002E, 0x2026])
        lines = result.strip().split("\n")
        all_text = " ".join(lines)
        # 0x002E should come before 0x003F which comes before 0x2026
        pos_2e = all_text.index("0x002E")
        pos_3f = all_text.index("0x003F")
        pos_2026 = all_text.index("0x2026")
        self.assertLess(pos_2e, pos_3f)
        self.assertLess(pos_3f, pos_2026)


# ---------------------------------------------------------------------------
# _render_module
# ---------------------------------------------------------------------------


class RenderModuleTests(unittest.TestCase):
    """Verify _render_module produces valid Python source."""

    def test_output_contains_version(self) -> None:
        result = generate_unicode_data._render_module(
            ucdVersion="17.0.0",
            cldrVersion="48.2",
            languageScripts={"en": ("Latin",)},
            scriptRanges={"Latin": ((0x0041, 0x005A),)},
            sentenceTerminals={0x002E, 0x003F},
        )
        self.assertIn('UNICODE_VERSION = "17.0.0"', result)
        self.assertIn('CLDR_VERSION = "48.2"', result)
        self.assertIn('"en":', result)
        self.assertIn("Latin", result)
        self.assertIn("SENTENCE_TERMINAL_CODEPOINTS", result)


if __name__ == "__main__":
    unittest.main()
