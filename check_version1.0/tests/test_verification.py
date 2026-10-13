"""No hardware required: validate parsing, configuration and actual UI signals."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from card_service import ApduExchange, CardService, CardServiceError, CommandResult
from main_window import CheckWindow


def response(value, command="80CA9F7F00", sw="9000"):
    return CommandResult(value, sw, (ApduExchange(command, value, sw),))


class VerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.settings_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.settings_folder.cleanup)
        self.settings_path = str(Path(self.settings_folder.name) / "preferences.ini")
        settings_patch = patch("main_window.QSettings", side_effect=lambda *args: QSettings(self.settings_path, QSettings.IniFormat))
        settings_patch.start()
        self.addCleanup(settings_patch.stop)
        with patch.object(CheckWindow, "refresh_readers"):
            self.window = CheckWindow()
        self.service = MagicMock(spec=CardService)
        self.service.connect.return_value = "3B00"
        self.service.select_isd.return_value = response("", "00A4040008A000000003000000")
        self.service.parse_cplc_value.side_effect = CardService.parse_cplc_value
        self.service.parse_de_value.side_effect = CardService.parse_de_value
        self.service.load_versions.side_effect = CardService.load_versions
        self.window.service = self.service
        self.window.ui.readerComboBox.blockSignals(True)
        self.window.ui.readerComboBox.addItem("Test reader", "Test reader")
        self.window.ui.readerComboBox.setCurrentIndex(0)
        self.window.ui.readerComboBox.blockSignals(False)
        self.window.reader_list = ["Test reader"]

    def tearDown(self):
        self.window.close()

    def test_cplc_value_and_tlv(self):
        for prefix in ("81002DD3484F", "9F7F2DD3484F"):
            value = prefix + "00" * 36
            for raw in (value, "9F7F2A" + value, "9F7F812A" + value):
                self.assertEqual(CardService.parse_cplc_value(raw), value)
        for raw in ("", "ZZ", "9F7F2A81002D", "9F7F00", "9F7F80", "00" * 43):
            with self.assertRaises(CardServiceError):
                CardService.parse_cplc_value(raw)

    def test_language_survives_restart(self):
        self.assertEqual(self.window.language, "zh")
        for index, language, label in ((1, "en", "Verify DE"), (0, "zh", "校验 DE")):
            self.window.ui.languageComboBox.setCurrentIndex(index)
            self.window.close()
            with patch.object(CheckWindow, "refresh_readers"):
                self.window = CheckWindow()
            self.assertEqual(self.window.language, language)
            self.assertEqual(self.window.ui.languageComboBox.currentIndex(), index)
            self.assertEqual(self.window.ui.checkDeButton.text(), label)

    def test_unknown_saved_language_defaults_to_chinese(self):
        self.window.settings.setValue("ui/language", "unknown")
        self.window.settings.sync()
        self.window.close()
        with patch.object(CheckWindow, "refresh_readers"):
            self.window = CheckWindow()
        self.assertEqual(self.window.language, "zh")
        self.assertEqual(self.window.ui.languageComboBox.currentIndex(), 0)

    def test_cplc_prefix_only_and_mismatch(self):
        for tail in ("00", "FF"):
            self.service.read_cplc.return_value = response("9F7F2A81002DD3484F" + tail * 36)
            self.window.ui.checkCplcButton.click()
            self.assertTrue(self.window.result_status)
        self.service.read_de.assert_not_called()
        self.service.read_cplc.return_value = response("9F7F2A81002DD34840" + "00" * 36)
        self.window.ui.checkCplcButton.click()
        self.assertFalse(self.window.result_status)

    def test_de_compatibility(self):
        self.service.read_de.return_value = response("DE02012B", "80CA00DE00")
        self.window.ui.checkDeButton.click()
        self.assertTrue(self.window.result_status)
        self.service.read_cplc.assert_not_called()
        self.service.read_de.return_value = response("DE020000", "80CA00DE00")
        self.window.ui.checkDeButton.click()
        self.assertFalse(self.window.result_status)

    def test_missing_and_invalid_config_does_not_pass(self):
        self.service.read_cplc.return_value = response("81002DD3484F" + "00" * 36)
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "version.ini"
            config.write_text("[CPLC]\nprefix_1=81\nprefix_2=ZZ002DD3484F\n", encoding="utf-8")
            self.assertEqual(len(CardService.load_versions(str(config), "CPLC", 6)[1]), 2)
            self.window.CONFIG_FILE = str(config)
            self.window.ui.checkCplcButton.click()
            self.assertFalse(self.window.result_status)
            self.window.CONFIG_FILE = str(Path(folder) / "missing.ini")
            self.window.ui.checkCplcButton.click()
            self.assertFalse(self.window.result_status)

    def test_language_and_clear_log(self):
        self.service.read_cplc.return_value = response("81002DD3484F" + "00" * 36)
        self.window.ui.checkCplcButton.click()
        history = self.window.ui.logTextEdit.toPlainText()
        self.window.ui.languageComboBox.setCurrentIndex(1)
        self.assertEqual(self.window.ui.checkCplcButton.text(), "Verify CPLC")
        self.assertEqual(self.window.ui.checkDeButton.text(), "Verify DE")
        self.assertEqual(self.window.ui.statusTextLabel.text(), "CPLC · Passed")
        self.assertEqual(self.window.ui.logTextEdit.toPlainText(), history)
        self.window.ui.clearLogButton.click()
        self.assertEqual(self.window.ui.logTextEdit.toPlainText(), "")
        self.assertTrue(self.window.result_status)
        self.window.ui.checkCplcButton.click()
        self.assertIn("CPLC verification passed", self.window.ui.logTextEdit.toPlainText())
        self.window.ui.languageComboBox.setCurrentIndex(0)
        self.assertEqual(self.window.ui.statusTextLabel.text(), "CPLC · 校验成功")

    def test_failures_and_english_errors(self):
        self.window.ui.languageComboBox.setCurrentIndex(1)
        self.service.connect.side_effect = CardService.readable_error(Exception("0x8010000C"))
        self.window.ui.checkCplcButton.click()
        self.assertIn("No card detected", self.window.ui.logTextEdit.toPlainText())
        self.assertFalse(self.window.result_status)
        self.service.read_cplc.assert_not_called()
        self.service.connect.side_effect = None
        self.service.select_isd.return_value = response("", sw="6A82")
        self.window.ui.checkDeButton.click()
        self.assertFalse(self.window.result_status)
        self.service.read_de.assert_not_called()
        self.window.reader_list = []
        self.window.ui.checkDeButton.click()
        self.assertIn("No valid reader", self.window.ui.logTextEdit.toPlainText())

    def test_cplc_get_response_and_length_retry(self):
        service = CardService()
        value = "81002DD3484F" + "00" * 36
        with patch.object(service, "send_once", side_effect=[
            ApduExchange("80CA9F7F00", "", "6C2D"),
            ApduExchange("80CA9F7F2D", "9F7F2A" + value[:12], "6124"),
            ApduExchange("00C0000024", value[12:], "9000"),
        ]) as sender:
            result = service.read_cplc()
        self.assertEqual([call.args[0] for call in sender.call_args_list],
                         ["80CA9F7F00", "80CA9F7F2D", "00C0000024"])
        self.assertEqual(CardService.parse_cplc_value(result.response), value)


if __name__ == "__main__":
    unittest.main()
