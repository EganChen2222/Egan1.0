import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from todo.service import TaskService
from todo.storage import SQLiteTaskRepository
from todo.ui.editor import TaskEditor
from todo.ui.icons import application_icon
from todo.ui.theme import STYLE
from todo.ui.window import MainWindow


class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.repo = SQLiteTaskRepository(root / 'tasks.sqlite3')
        self.service = TaskService(self.repo)
        self.window = MainWindow(self.service, QSettings(str(root / 'settings.ini'),
                                 QSettings.Format.IniFormat), application_icon(root), enable_tray=False)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.repo.close()
        self.temp.cleanup()

    def capture(self, text):
        self.window.capture.setText(text)
        QTest.keyClick(self.window.capture, Qt.Key.Key_Return)
        self.app.processEvents()

    def test_capture_complete_reopen_delete_undo(self):
        self.capture('第一件事')
        self.assertEqual(len(self.window.cards), 1)
        self.assertEqual(self.window.capture.text(), '')
        self.window.cards[0].checkbox.click()
        self.assertEqual(len(self.window.cards), 0)
        self.window.nav['completed'].click()
        self.assertEqual(len(self.window.cards), 1)
        self.window.cards[0].checkbox.click()
        self.window.nav['inbox'].click()
        self.window.cards[0].delete_button.click()
        self.assertEqual(len(self.service.all()), 0)
        self.window.undo_button.click()
        self.assertEqual(self.service.all()[0].title, '第一件事')

    def test_today_default_and_search(self):
        self.window.nav['today'].click()
        self.capture('今天记录')
        self.assertEqual(self.service.all()[0].due, date.today())
        self.window.search.setText('不存在')
        self.assertEqual(len(self.window.cards), 0)
        self.window.search.clear()
        self.window.cards[0].star_button.click()
        self.window.nav['important'].click()
        self.assertEqual(len(self.window.cards), 1)

    def test_failed_capture_preserves_input_and_does_not_claim_saved(self):
        self.window.capture.setText('保留草稿')
        with patch.object(self.service, 'add', side_effect=OSError('disk full')):
            with patch.object(QMessageBox, 'warning') as warning:
                with self.assertLogs(level='ERROR'):
                    self.window.quick_add()
        warning.assert_called_once()
        self.assertEqual(self.window.capture.text(), '保留草稿')
        self.assertEqual(self.service.all(), [])

    def test_editor_validation_and_optional_date(self):
        editor = TaskEditor(parent=self.window)
        editor.validate_and_accept()
        self.assertNotEqual(editor.result(), QDialog.DialogCode.Accepted)
        editor.title_input.setText('标题')
        self.assertIsNone(editor.values()['due'])
        editor.has_due.setChecked(True)
        self.assertEqual(editor.values()['due'], date.today())
        editor.validate_and_accept()
        self.assertEqual(editor.result(), QDialog.DialogCode.Accepted)

    def test_global_wake_restores_hidden_window_and_preserves_draft(self):
        self.window.capture.setText('未写完的草稿')
        self.window.change_view('important')
        self.window.search.setText('过滤词')
        self.window.hide()
        self.window.wake_for_capture()
        QTest.qWait(20)
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.window.view, 'inbox')
        self.assertEqual(self.window.search.text(), '')
        # Offscreen cannot own desktop focus; verify the requested focus widget.
        self.assertIs(self.window.focusWidget(), self.window.capture)
        self.assertEqual(self.window.capture.text(), '未写完的草稿')
        self.assertEqual(self.window.capture.selectedText(), '')
        self.assertEqual(self.window.capture.cursorPosition(), len('未写完的草稿'))

    def test_global_wake_keeps_modal_editor_and_draft(self):
        editor = TaskEditor(parent=self.window)
        editor.title_input.setText('正在编辑')
        editor.setModal(True)
        editor.show()
        self.app.processEvents()
        self.window.wake_for_capture()
        self.app.processEvents()
        self.assertIs(QApplication.activeModalWidget(), editor)
        self.assertEqual(editor.title_input.text(), '正在编辑')
        editor.close()


if __name__ == '__main__':
    unittest.main()
