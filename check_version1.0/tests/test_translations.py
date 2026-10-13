"""Guard translation completeness and dynamic placeholder contracts."""
import ast
import sys
import tempfile
import unittest
from pathlib import Path
from string import Formatter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from translations import DEFAULT_TEXTS, TEXTS, load_texts, translate, translation_path


class TranslationTests(unittest.TestCase):
    def test_external_text_is_loaded_and_can_be_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "translations.ini"
            path.write_text('[verify_de]\nzh = "检查 DE"\nen = "Check DE 100%"\n', encoding="utf-8-sig")
            loaded = load_texts(path)
            with patch("translations.TEXTS", loaded):
                self.assertEqual(translate("verify_de", "zh"), "检查 DE")
                self.assertEqual(translate("verify_de", "en"), "Check DE 100%")
            path.write_text('[verify_de]\nzh = "验证 DE"\n', encoding="utf-8")
            self.assertEqual(load_texts(path)["verify_de"]["zh"], "验证 DE")
            self.assertEqual(load_texts(path)["verify_de"]["en"], DEFAULT_TEXTS["verify_de"]["en"])

    def test_invalid_entries_fall_back_individually(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "translations.ini"
            path.write_text('[current_reader]\nen = "Reader: {wrong}"\n'
                            '[verify_de]\nen = "Custom DE"\nzh = broken\n'
                            '[clear_log]\nen = 12\n', encoding="utf-8")
            loaded = load_texts(path)
            self.assertEqual(loaded["current_reader"], DEFAULT_TEXTS["current_reader"])
            self.assertEqual(loaded["verify_de"]["en"], "Custom DE")
            self.assertEqual(loaded["verify_de"]["zh"], DEFAULT_TEXTS["verify_de"]["zh"])
            self.assertEqual(loaded["clear_log"], DEFAULT_TEXTS["clear_log"])
            path.write_text('invalid ini', encoding="utf-8")
            self.assertEqual(load_texts(path), DEFAULT_TEXTS)
            self.assertEqual(load_texts(Path(folder) / "missing.ini"), DEFAULT_TEXTS)

    def test_spaces_newlines_and_literal_braces_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "translations.ini"
            path.write_text('[current_reader]\nen = "\\nReader {{device}}: {reader} "\n', encoding="utf-8")
            with patch("translations.TEXTS", load_texts(path)):
                self.assertEqual(translate("current_reader", "en", reader="USB"), '\nReader {device}: USB ')

    def test_frozen_app_reads_config_next_to_executable(self):
        with patch("sys.frozen", True, create=True), patch("sys.executable", str(ROOT / "dist" / "App.exe")):
            self.assertEqual(translation_path(), ROOT / "dist" / "config" / "translations.ini")

    def test_shipped_ini_contains_all_default_texts(self):
        import configparser
        import json
        config = configparser.ConfigParser(interpolation=None)
        config.read(ROOT / "config" / "translations.ini", encoding="utf-8-sig")
        self.assertEqual(set(config.sections()), set(DEFAULT_TEXTS))
        for key, entry in DEFAULT_TEXTS.items():
            for language, value in entry.items():
                self.assertEqual(json.loads(config[key][language]), value)

    def test_languages_and_placeholders_match(self):
        for key, entry in TEXTS.items():
            with self.subTest(key=key):
                self.assertEqual(set(entry), {"zh", "en"})
                fields = [{name for _, name, _, _ in Formatter().parse(entry[lang])
                           if name is not None} for lang in ("zh", "en")]
                self.assertEqual(fields[0], fields[1])
                for language in ("zh", "en"):
                    self.assertTrue(translate(key, language, **{name: "sample" for name in fields[0]}))

    def test_call_sites_supply_required_placeholders(self):
        for filename in ("main_window.py", "card_service.py"):
            tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr not in ("tr_text", "from_key") or not node.args:
                    continue
                if not isinstance(node.args[0], ast.Constant):
                    continue
                key = node.args[0].value
                with self.subTest(file=filename, line=node.lineno, key=key):
                    self.assertIn(key, TEXTS)
                    expected = {name for _, name, _, _ in Formatter().parse(TEXTS[key]["zh"])
                                if name is not None}
                    self.assertEqual(expected, {kw.arg for kw in node.keywords})

    def test_language_fallback_and_dynamic_values(self):
        self.assertEqual(translate("verify_de", "unknown"), "校验 DE")
        self.assertEqual(translate("invalid_setting", "en", key="prefix_1", rule="invalid"),
                         "Ignoring invalid setting prefix_1 (invalid)")
        self.assertEqual(translate("current_reader", "en", reader="Reader {1}"),
                         "Current reader: Reader {1}")


if __name__ == "__main__":
    unittest.main()
