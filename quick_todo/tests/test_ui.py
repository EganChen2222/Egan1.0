import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import time
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QDate, QSettings, QTime, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from todo.service import TaskService
from todo.storage import SQLiteTaskRepository
from todo.ui.editor import TaskEditor
from todo.ui.icons import application_icon
from todo.ui.theme import STYLE
from todo.ui.window import MainWindow
from todo.ui.reminders import ReminderSettings
from todo.ui.scheduled_reminders import ScheduledReminderEditor, ScheduledRemindersDialog


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

    def test_reminder_random_days_and_restart_preserves_deadline(self):
        reminders = self.window.reminders
        self.assertEqual((reminders.minimum, reminders.maximum, reminders.seconds), (24, 48, 6))
        now = time.time()
        self.assertGreaterEqual(reminders.next_due_at, now + 24 * 3600 - 2)
        self.assertLessEqual(reminders.next_due_at, now + 48 * 3600)
        deadline = reminders.next_due_at
        reminders.stop()
        reminders.schedule(resume=True)
        self.assertEqual(reminders.next_due_at, deadline)
        # 每轮重新抽取秒级间隔，并保存到磁盘。
        with patch('todo.ui.reminders.random.randint', return_value=30 * 3600) as draw:
            reminders.schedule()
        draw.assert_called_once_with(24 * 3600, 48 * 3600)
        saved = QSettings(self.window.settings.fileName(), QSettings.Format.IniFormat)
        self.assertEqual(float(saved.value('reminders/next_due_at')), reminders.next_due_at)

    def test_reminder_ignores_view_search_and_completed_tasks(self):
        self.capture('未完成事项')
        done = self.service.add('已经完成')
        self.service.complete(done, True)
        self.window.change_view('completed')
        self.window.search.setText('无匹配')
        self.window.hide()
        reminders = self.window.reminders
        reminders.next_due_at = time.time() - 1
        reminders.on_timeout()
        self.assertTrue(reminders.popup.isVisible())
        self.assertFalse(self.window.isVisible())
        self.assertEqual(reminders.popup.summary.text(), '还有 1 件待办未完成')
        self.assertIn('未完成事项', reminders.popup.detail.text())
        self.assertNotIn('已经完成', reminders.popup.detail.text())
        self.assertTrue(reminders.timer.isActive())
        self.assertGreater(reminders.next_due_at, time.time() + 23 * 3600)
        self.assertTrue(reminders.popup.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating))
        self.assertTrue(reminders.popup.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)
        reminders.popup.open_button.click()
        self.assertFalse(reminders.popup.isVisible())
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.window.view, 'inbox')

    def test_reminder_does_not_fire_early_and_empty_list_stays_quiet(self):
        reminders = self.window.reminders
        self.capture('稍后提醒')
        reminders.on_timeout()
        self.assertFalse(reminders.popup.isVisible())
        self.window.cards[0].checkbox.click()
        reminders.next_due_at = time.time() - 1
        reminders.on_timeout()
        self.assertFalse(reminders.popup.isVisible())
        self.assertTrue(reminders.timer.isActive())

    def test_reminder_auto_hides_and_disable_persists(self):
        self.capture('记得处理')
        reminders = self.window.reminders
        reminders.configure(True, 24, 48, 2)
        reminders.show_now()
        self.assertEqual(reminders.popup.hint.text(), '2 秒后自动关闭')
        QTest.qWait(1200)
        self.assertTrue(reminders.popup.isVisible())
        self.assertEqual(reminders.popup.hint.text(), '1 秒后自动关闭')
        QTest.qWait(1000)
        self.assertFalse(reminders.popup.isVisible())
        self.assertFalse(reminders.popup.countdown_timer.isActive())
        reminders.show_now()
        self.assertEqual(reminders.popup.hint.text(), '2 秒后自动关闭')
        reminders.configure(False, 25, 47, 6)
        self.assertFalse(reminders.timer.isActive())
        self.assertFalse(reminders.popup.isVisible())
        self.assertFalse(reminders.popup.countdown_timer.isActive())
        saved = QSettings(self.window.settings.fileName(), QSettings.Format.IniFormat)
        self.assertFalse(saved.value('reminders/enabled', True, type=bool))
        self.assertEqual(saved.value('reminders/minimum_hours', type=int), 25)

    def test_reminder_read_failure_retries_later_and_completion_dismisses(self):
        self.capture('待处理')
        reminders = self.window.reminders
        reminders.show_now()
        self.window.cards[0].checkbox.click()
        self.assertFalse(reminders.popup.isVisible())
        reminders.next_due_at = time.time() - 1
        with patch.object(self.service, 'all', side_effect=OSError('read failed')):
            with self.assertLogs(level='ERROR'):
                reminders.on_timeout()
        self.assertTrue(reminders.timer.isActive())
        self.assertFalse(reminders.popup.isVisible())

    def test_reminder_settings_reject_reversed_range(self):
        dialog = ReminderSettings(self.window.reminders, self.window)
        dialog.minimum.setValue(48)
        dialog.maximum.setValue(24)
        dialog.validate_and_accept()
        self.assertNotEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertTrue(dialog.error.text())
        dialog.maximum.setValue(48)
        dialog.validate_and_accept()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        dialog.deleteLater()

    def test_scheduled_fires_from_timer_when_random_disabled_and_no_tasks(self):
        now = datetime(2026, 10, 13, 16, 0)
        at = now.replace(hour=17, minute=30)
        self.service.save_reminder('关闭节点', at, now=now)
        controller = self.window.reminders
        controller.configure(False, 24, 48, 6)
        self.window.hide()
        with patch('todo.ui.reminders.datetime') as clock:
            clock.now.return_value = at
            QTest.qWait(1200)
        self.assertTrue(controller.popup.isVisible())
        self.assertFalse(self.window.isVisible())
        self.assertEqual(controller.popup.detail.text(), '关闭节点')
        self.assertIn('17:30', controller.popup.summary.text())
        self.assertTrue(controller.popup.is_scheduled)
        self.window.refresh()  # 空的待办列表不能关闭定时事件小窗。
        self.assertTrue(controller.popup.isVisible())
        controller.popup.open_button.click()
        self.assertFalse(controller.popup.isVisible())
        self.assertFalse(self.window.isVisible())

    def test_scheduled_events_queue_without_random_overwriting_them(self):
        now = datetime(2026, 10, 13, 16, 0)
        at = now.replace(hour=17, minute=30)
        for title in ('事件一', '事件二'):
            self.service.save_reminder(title, at, now=now)
        controller = self.window.reminders
        with patch('todo.ui.reminders.datetime') as clock:
            clock.now.return_value = at
            controller.check_scheduled()
            first = controller.popup.detail.text()
            controller.show_now()
            self.assertEqual(controller.popup.detail.text(), first)
            self.assertEqual(sum(r.enabled for r in self.service.reminders()), 1)
            controller.popup.dismiss()
            controller.check_scheduled()
            self.assertNotEqual(controller.popup.detail.text(), first)
            self.assertFalse(any(r.enabled for r in self.service.reminders()))

    def test_main_scheduled_button_and_editor_save_delete(self):
        observations = []
        def check_manager():
            manager = QApplication.activeModalWidget()
            observations.append(isinstance(manager, ScheduledRemindersDialog))
            manager.reject()
        QTimer.singleShot(0, check_manager)
        self.window.scheduled_button.click()
        self.assertEqual(observations, [True])
        manager = ScheduledRemindersDialog(self.service, self.window.reminders, self.window)
        future = datetime.now() + timedelta(days=1)
        def fill_editor():
            editor = QApplication.activeModalWidget()
            editor.title_input.setText('关闭节点')
            editor.date_input.setDate(QDate(future.year, future.month, future.day))
            editor.time_input.setTime(QTime(17, 30))
            editor.validate_and_accept()
        QTimer.singleShot(0, fill_editor)
        manager.add_button.click()
        self.assertEqual(len(self.service.reminders()), 1)
        self.assertEqual(self.service.reminders()[0].next_at.hour, 17)
        self.assertEqual(self.service.reminders()[0].next_at.minute, 30)
        manager.items.setCurrentItem(manager.items.topLevelItem(0))
        manager.delete_button.click()
        self.assertEqual(self.service.reminders(), [])
        manager.deleteLater()

    def test_scheduled_editor_rejects_past_time_and_daily_ignores_date(self):
        editor = ScheduledReminderEditor(parent=self.window)
        editor.title_input.setText('关闭节点')
        editor.date_input.setDate(QDate(2020, 1, 1))
        editor.validate_and_accept()
        self.assertNotEqual(editor.result(), QDialog.DialogCode.Accepted)
        editor.daily.setChecked(True)
        self.assertFalse(editor.date_input.isEnabled())
        editor.validate_and_accept()
        self.assertEqual(editor.result(), QDialog.DialogCode.Accepted)
        editor.deleteLater()


if __name__ == '__main__':
    unittest.main()
