from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import build_i18n


class TranslationTemplateUpdateTests(unittest.TestCase):
	def test_update_command_accepts_all_and_multiple_languages(self) -> None:
		language_dirs = [build_i18n.LOCALE_DIR / "ru", build_i18n.LOCALE_DIR / "uk"]
		cases = (
			(["--all-languages"], None),
			(["--language", "ru", "--language", "uk"], ["ru", "uk"]),
		)
		for selection_arguments, expected_selection in cases:
			with (
				self.subTest(selection_arguments=selection_arguments),
				mock.patch.object(
					build_i18n.sys,
					"argv",
					["build_i18n.py", "--update-po", *selection_arguments],
				),
				mock.patch.object(build_i18n, "_translatable_source_messages", return_value={"New": []}),
				mock.patch.object(build_i18n, "_write_pot", return_value=build_i18n.POT_PATH),
				mock.patch.object(
					build_i18n,
					"_language_dirs",
					return_value=(language_dirs, []),
				) as language_dirs_mock,
				mock.patch.object(build_i18n, "_find_msgmerge", return_value=Path("msgmerge")),
				mock.patch.object(
					build_i18n,
					"_update_po_from_template",
					return_value=(1, 1, 1),
				) as update_mock,
				mock.patch("builtins.print"),
			):
				result = build_i18n.main()

			self.assertEqual(0, result)
			language_dirs_mock.assert_called_once_with(expected_selection)
			self.assertEqual(2, update_mock.call_count)

	def test_update_menu_can_select_one_or_all_locales(self) -> None:
		with (
			mock.patch.object(build_i18n, "_addon_languages", return_value=["ru", "uk"]),
			mock.patch("builtins.input", side_effect=["3", "1"]),
			mock.patch("builtins.print"),
		):
			all_options = build_i18n._interactive_options(build_i18n.DEFAULT_CHECKS)
		with (
			mock.patch.object(build_i18n, "_addon_languages", return_value=["ru", "uk"]),
			mock.patch("builtins.input", side_effect=["3", "3"]),
			mock.patch("builtins.print"),
		):
			one_options = build_i18n._interactive_options(build_i18n.DEFAULT_CHECKS)

		self.assertIsNone(all_options[0])
		self.assertTrue(all_options[4])
		self.assertEqual(["uk"], one_options[0])
		self.assertTrue(one_options[4])

	def test_pot_project_version_comes_from_manifest(self) -> None:
		with tempfile.TemporaryDirectory() as temporary_directory:
			root = Path(temporary_directory)
			manifest_path = root / "manifest.ini"
			pot_path = root / "nvda.pot"
			manifest_path.write_text("version = 9.8.7\n", encoding="utf-8")
			with (
				mock.patch.object(build_i18n, "MANIFEST_SOURCE", manifest_path),
				mock.patch.object(build_i18n, "POT_PATH", pot_path),
			):
				build_i18n._write_pot({})
			text = pot_path.read_text(encoding="utf-8")
			self.assertIn("Project-Id-Version: Google TTS For NVDA 9.8.7", text)

	def test_purge_obsolete_entries_removes_complete_blocks(self) -> None:
		text = """# Header comment

msgid ""
msgstr "Language: uk\\n"

#: current.py:1
msgid "Current"
msgstr "Поточний"

#, python-brace-format
#~ msgid "Old {name}"
#~ msgstr "Старий {name}"
"""
		updated, removed = build_i18n._purge_obsolete_po_entries(text)
		self.assertEqual(1, removed)
		self.assertIn('msgid "Current"', updated)
		self.assertNotIn("Old {name}", updated)

	def test_update_adds_empty_strings_and_removes_obsolete_entries(self) -> None:
		with tempfile.TemporaryDirectory() as temporary_directory:
			root = Path(temporary_directory)
			language_dir = root / "uk"
			messages_dir = language_dir / "LC_MESSAGES"
			messages_dir.mkdir(parents=True)
			po_path = messages_dir / "nvda.po"
			pot_path = root / "nvda.pot"
			original = """msgid ""
msgstr ""
"Language: uk\\n"
"Last-Translator: Translator\\n"

msgid "Keep"
msgstr "Зберегти"

msgid "Old active"
msgstr "Старий"
"""
			po_path.write_text(original, encoding="utf-8")
			pot_path.write_text("template", encoding="utf-8")
			merged = """msgid ""
msgstr ""
"Language: uk\\n"
"Last-Translator: Translator\\n"

#: current.py:1
msgid "Keep"
msgstr "Зберегти"

#: current.py:2
msgid "New"
msgstr ""

#~ msgid "Old active"
#~ msgstr "Старий"

#~ msgid "Older obsolete"
#~ msgstr "Давній"
"""

			def fake_run(arguments: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
				output_index = arguments.index("--output-file") + 1
				Path(arguments[output_index]).write_text(merged, encoding="utf-8")
				return subprocess.CompletedProcess(arguments, 0, "", "")

			with (
				mock.patch.object(build_i18n, "POT_PATH", pot_path),
				mock.patch.object(build_i18n.subprocess, "run", side_effect=fake_run),
			):
				preserved, added, removed = build_i18n._update_po_from_template(
					language_dir,
					Path("msgmerge"),
					{"Keep": ["current.py:1"], "New": ["current.py:2"]},
				)

			self.assertEqual((1, 1, 2), (preserved, added, removed))
			catalog = build_i18n._parse_po(po_path, include_untranslated=True)
			self.assertEqual("Зберегти", catalog["Keep"])
			self.assertEqual("", catalog["New"])
			self.assertNotIn("Old active", catalog)
			self.assertIn("Last-Translator: Translator", catalog[""])
			self.assertNotIn("#~", po_path.read_text(encoding="utf-8"))

	def test_update_rejects_nonempty_translation_for_new_string(self) -> None:
		with tempfile.TemporaryDirectory() as temporary_directory:
			root = Path(temporary_directory)
			language_dir = root / "uk"
			messages_dir = language_dir / "LC_MESSAGES"
			messages_dir.mkdir(parents=True)
			po_path = messages_dir / "nvda.po"
			pot_path = root / "nvda.pot"
			original = 'msgid ""\nmsgstr "Language: uk\\n"\n'
			po_path.write_text(original, encoding="utf-8")
			pot_path.write_text("template", encoding="utf-8")
			merged = """msgid ""
msgstr "Language: uk\\n"

msgid "New"
msgstr "Guessed translation"
"""

			def fake_run(arguments: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
				output_index = arguments.index("--output-file") + 1
				Path(arguments[output_index]).write_text(merged, encoding="utf-8")
				return subprocess.CompletedProcess(arguments, 0, "", "")

			with (
				mock.patch.object(build_i18n, "POT_PATH", pot_path),
				mock.patch.object(build_i18n.subprocess, "run", side_effect=fake_run),
				self.assertRaisesRegex(RuntimeError, "new source strings received non-empty translations"),
			):
				build_i18n._update_po_from_template(
					language_dir,
					Path("msgmerge"),
					{"New": ["current.py:1"]},
				)
			self.assertEqual(original, po_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
	unittest.main()
