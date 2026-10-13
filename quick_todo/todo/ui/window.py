import logging
from datetime import date
from typing import Optional

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QMenu, QMessageBox, QPushButton, QScrollArea,
                               QSystemTrayIcon, QVBoxLayout, QWidget)

from ..domain import Task
from ..service import TaskService
from .editor import TaskEditor
from .reminders import ReminderController, ReminderSettings
from .scheduled_reminders import ScheduledRemindersDialog
from .task_card import TaskCard


VIEWS = {
    'inbox': ('全部待办', '把想法写下来，把注意力留给当下。'),
    'today': ('今天', '先照顾今天到期和还未完成的事情。'),
    'important': ('重要', '为真正值得投入的事情，留一点空间。'),
    'completed': ('已完成', '每一个小小的完成，都算数。'),
}


class MainWindow(QMainWindow):
    def __init__(self, service: TaskService, settings: QSettings,
                 icon: QIcon, enable_tray: bool = True):
        super().__init__()
        self.service = service
        self.settings = settings
        self.view = 'inbox'
        self.deleted_task: Optional[Task] = None
        self.quitting = False
        self.tray = None
        self.foreground_request = lambda window_id: None
        self.setWindowTitle('轻记 · 待办')
        self.setWindowIcon(icon)
        self.resize(960, 680)
        self.setMinimumSize(760, 520)
        self.build_ui()
        geometry = settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)
        self.pin.setChecked(settings.value('pinned', False, type=bool))
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.pin.isChecked())
        self.pin.toggled.connect(self.set_pinned)
        self.reminders = ReminderController(service, settings, self)
        self.reminders.popup.open_requested.connect(self.wake_for_capture)
        self.shortcuts = []
        for keys, callback in [('Ctrl+N', self.focus_capture), ('Ctrl+F', self.search.setFocus),
                               ('Ctrl+Return', self.new_details)]:
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        if enable_tray and QSystemTrayIcon.isSystemTrayAvailable():
            self.setup_tray(icon)
        self.refresh()
        self.day = date.today()
        self.day_timer = QTimer(self)
        self.day_timer.setInterval(30000)
        self.day_timer.timeout.connect(self.check_day)
        self.day_timer.start()

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(16, 16, 24, 16)
        outer.setSpacing(28)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(178)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 20, 14, 14)
        side.setSpacing(6)
        brand = QLabel('轻记')
        brand.setObjectName('brand')
        side.addWidget(brand)
        tag = QLabel('随手记，慢慢完成')
        tag.setObjectName('muted')
        side.addWidget(tag)
        side.addSpacing(16)
        self.nav = {}
        for key, (label, _) in VIEWS.items():
            button = QPushButton(label)
            button.setObjectName('nav')
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, view=key: self.change_view(view))
            self.nav[key] = button
            side.addWidget(button)
        side.addStretch()
        self.pin = QCheckBox('窗口置顶')
        side.addWidget(self.pin)
        hint = QLabel('Ctrl + N  快速记录\nCtrl + F  搜索\nCtrl + Enter  新建')
        hint.setObjectName('muted')
        side.addSpacing(12)
        self.hotkey_hint = QLabel('桌面快捷键未启用')
        self.hotkey_hint.setObjectName('muted')
        self.hotkey_hint.setWordWrap(True)
        side.addWidget(self.hotkey_hint)
        side.addWidget(hint)
        local = QLabel('仅保存在本机')
        local.setObjectName('muted')
        side.addSpacing(10)
        side.addWidget(local)
        outer.addWidget(sidebar)
        main = QVBoxLayout()
        main.setContentsMargins(0, 14, 0, 0)
        main.setSpacing(16)
        top = QHBoxLayout()
        self.date_label = QLabel()
        self.date_label.setObjectName('muted')
        top.addWidget(self.date_label)
        top.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索当前列表…')
        self.search.setAccessibleName('搜索当前列表的标题和备注')
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(220)
        self.search.textChanged.connect(self.refresh)
        top.addWidget(self.search)
        main.addLayout(top)
        heading_row = QHBoxLayout()
        self.heading = QLabel()
        self.heading.setObjectName('heading')
        heading_row.addWidget(self.heading)
        heading_row.addStretch()
        self.scheduled_button = QPushButton('定时提醒')
        self.scheduled_button.setObjectName('reminderSettings')
        self.scheduled_button.setToolTip('在指定时间提醒一件事，支持单次或每天重复')
        self.scheduled_button.clicked.connect(self.edit_scheduled_reminders)
        heading_row.addWidget(self.scheduled_button)
        self.reminder_settings_button = QPushButton('提醒设置')
        self.reminder_settings_button.setObjectName('reminderSettings')
        self.reminder_settings_button.setToolTip('调整随机提醒间隔、显示时长，或关闭提醒')
        self.reminder_settings_button.clicked.connect(self.edit_reminder_settings)
        heading_row.addWidget(self.reminder_settings_button)
        main.addLayout(heading_row)
        self.subtitle = QLabel()
        self.subtitle.setObjectName('muted')
        main.addWidget(self.subtitle)
        capture_row = QHBoxLayout()
        capture_row.setSpacing(8)
        self.capture = QLineEdit()
        self.capture.setObjectName('capture')
        self.capture.setPlaceholderText('记下一件事，按 Enter 添加…')
        self.capture.setAccessibleName('快速记录待办')
        self.capture.setMaxLength(200)
        self.capture.returnPressed.connect(self.quick_add)
        capture_row.addWidget(self.capture, 1)
        self.add_button = QPushButton('＋ 添加')
        self.add_button.setObjectName('primary')
        self.add_button.setMinimumHeight(49)
        self.add_button.clicked.connect(self.quick_add)
        capture_row.addWidget(self.add_button)
        details = QPushButton('详细')
        details.setMinimumHeight(49)
        details.setToolTip('添加备注、截止日期和重要标记')
        details.clicked.connect(self.new_details)
        capture_row.addWidget(details)
        main.addLayout(capture_row)
        self.summary = QLabel()
        self.summary.setObjectName('muted')
        main.addWidget(self.summary)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main.addWidget(self.scroll, 1)
        bottom = QHBoxLayout()
        self.status = QLabel('准备好，开始记录吧。')
        self.status.setObjectName('muted')
        self.status.setWordWrap(True)
        bottom.addWidget(self.status, 1)
        self.undo_button = QPushButton('撤销删除')
        self.undo_button.setVisible(False)
        self.undo_button.clicked.connect(self.undo_delete)
        bottom.addWidget(self.undo_button)
        main.addLayout(bottom)
        outer.addLayout(main, 1)

    def change_view(self, view):
        self.view = view
        self.refresh()

    def refresh(self):
        try:
            tasks = self.service.all()
        except Exception:
            logging.exception('读取待办失败')
            self.status.setText('读取失败，请检查数据目录后重新打开。')
            return
        selected = self.service.select(tasks, self.view, self.search.text())
        if not self.reminders.popup.is_scheduled and not any(not task.completed for task in tasks):
            self.reminders.popup.dismiss()
        self.date_label.setText(date.today().strftime('%Y / %m / %d') + '  ·  ' +
                                ('星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日')[date.today().weekday()])
        self.heading.setText(VIEWS[self.view][0])
        self.subtitle.setText(VIEWS[self.view][1])
        for key, button in self.nav.items():
            button.setText('{}   {}'.format(VIEWS[key][0], len(self.service.select(tasks, key))))
            button.setChecked(key == self.view)
        completed = sum(t.completed for t in tasks)
        self.summary.setText('{} 项{}  ·  累计完成 {} 项'.format(
            len(selected), '搜索结果' if self.search.text().strip() else '记录', completed))
        scroll_position = self.scroll.verticalScrollBar().value()
        body = QWidget()
        body.setObjectName('taskList')
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(10)
        self.cards = []
        for task in selected:
            card = TaskCard(task)
            card.completed_changed.connect(lambda value, t=task: self.perform(
                lambda: self.service.complete(t, value), '已完成，做得好。' if value else '已重新打开。'))
            card.important_changed.connect(lambda value, t=task: self.perform(
                lambda: self.service.star(t, value), '重要标记已更新。'))
            card.edit_requested.connect(lambda t=task: self.edit_task(t))
            card.delete_requested.connect(lambda t=task: self.delete_task(t))
            layout.addWidget(card)
            self.cards.append(card)
        if not selected:
            layout.addStretch()
            symbol = QLabel('✓')
            symbol.setObjectName('emptyIcon')
            symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(symbol)
            title = QLabel('没有找到相关记录' if self.search.text().strip() else {
                'inbox': '此刻，轻装上阵', 'today': '今天没有到期待办',
                'important': '给重要的事一颗星', 'completed': '期待你的第一个完成',
            }[self.view])
            title.setObjectName('emptyTitle')
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title)
            hint = QLabel('试试其他关键词，或切换列表。' if self.search.text().strip()
                          else '在上方写下一件小事，从这里开始。')
            hint.setObjectName('muted')
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hint)
        layout.addStretch()
        old = self.scroll.takeWidget()
        self.scroll.setWidget(body)
        if old:
            old.deleteLater()
        self.scroll.verticalScrollBar().setValue(scroll_position)

    def perform(self, operation, message):
        try:
            operation()
        except ValueError as error:
            QMessageBox.information(self, '检查一下', str(error))
            self.refresh()
            return False
        except Exception:
            logging.exception('保存待办失败')
            QMessageBox.warning(self, '未能保存', '这次操作未能保存，请检查磁盘空间和数据目录权限后重试。')
            self.refresh()
            return False
        self.refresh()
        self.status.setText(message)
        return True

    def quick_add(self):
        due = date.today() if self.view == 'today' else None
        if self.perform(lambda: self.service.add(self.capture.text(), due=due,
                                                important=self.view == 'important'), '已添加，自动保存。'):
            self.capture.clear()
            self.search.clear()
            if self.view == 'completed':
                self.change_view('inbox')
            self.capture.setFocus()

    def new_details(self):
        editor = TaskEditor(parent=self)
        editor.title_input.setText(self.capture.text())
        editor.has_due.setChecked(self.view == 'today')
        editor.important_input.setChecked(self.view == 'important')
        while editor.exec() == QDialog.DialogCode.Accepted:
            if self.perform(lambda: self.service.add(**editor.values()), '已添加，自动保存。'):
                self.capture.clear()
                self.search.clear()
                if self.view == 'completed':
                    self.change_view('inbox')
                break

    def edit_task(self, task):
        editor = TaskEditor(task, self)
        while editor.exec() == QDialog.DialogCode.Accepted:
            if self.perform(lambda: self.service.edit(task, **editor.values()), '修改已保存。'):
                break

    def delete_task(self, task):
        if self.perform(lambda: self.service.delete(task), '已删除，可撤销最近一次删除。'):
            self.deleted_task = task
            self.undo_button.show()

    def undo_delete(self):
        if self.deleted_task and self.perform(lambda: self.service.restore(self.deleted_task), '已恢复删除的记录。'):
            self.deleted_task = None
            self.undo_button.hide()

    def focus_capture(self):
        self.show_window()
        self.capture.setFocus()
        self.capture.selectAll()

    def wake_for_capture(self):
        # Preserve any modal editor and its draft instead of focusing behind it.
        modal = QApplication.activeModalWidget()
        target = modal or self
        if target.isMinimized():
            target.showNormal()
        else:
            target.show()
        target.raise_()
        self.foreground_request(int(target.winId()))
        target.activateWindow()
        if modal:
            QTimer.singleShot(0, self._focus_after_wake)
            return
        self.view = 'inbox'
        self.search.clear()
        self.refresh()
        self.capture.setFocus(Qt.FocusReason.ShortcutFocusReason)
        # Continue an unfinished draft; waking up must not select/replace it.
        self.capture.setCursorPosition(len(self.capture.text()))
        # Hide/minimize activation events can still be queued by the platform.
        QTimer.singleShot(0, self._focus_after_wake)

    def _focus_after_wake(self):
        modal = QApplication.activeModalWidget()
        target = modal or self
        if not target.isVisible():
            return
        target.activateWindow()
        if not modal:
            self.capture.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def set_hotkey_status(self, enabled, message):
        self.hotkey_hint.setText('Ctrl + 空格  桌面速记' if enabled else '桌面快捷键未启用')
        self.hotkey_hint.setToolTip(message)
        if not enabled:
            self.status.setText(message)
            if self.tray:
                self.tray.showMessage('桌面快捷键', message)

    def set_pinned(self, pinned):
        self.settings.setValue('pinned', pinned)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, pinned)
        self.show()

    def check_day(self):
        if self.day != date.today():
            self.day = date.today()
            self.refresh()

    def edit_reminder_settings(self):
        dialog = ReminderSettings(self.reminders, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reminders.configure(*dialog.values())
            self.status.setText('提醒设置已保存。')
        dialog.deleteLater()

    def edit_scheduled_reminders(self):
        dialog = ScheduledRemindersDialog(self.service, self.reminders, self)
        dialog.exec()
        dialog.deleteLater()

    def preview_reminder(self):
        self.reminders.show_now()
        if not self.reminders.popup.isVisible():
            self.status.setText('当前没有可提醒的待办；读取失败时请查看日志。')

    def setup_tray(self, icon):
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip('轻记 · 点击打开，随手记录')
        menu = QMenu(self)
        for text, callback in [('打开轻记', self.show_window), ('快速记录', self.focus_capture),
                               ('提醒设置', self.edit_reminder_settings),
                               ('定时提醒', self.edit_scheduled_reminders),
                               ('立即提醒', self.preview_reminder),
                               ('退出', self.quit_app)]:
            action = QAction(text, menu)
            action.triggered.connect(callback)
            menu.addAction(action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.focus_capture()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def save_settings(self):
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.sync()

    def quit_app(self):
        self.quitting = True
        self.reminders.stop()
        self.save_settings()
        if self.tray:
            self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        self.save_settings()
        if self.tray and self.tray.isVisible() and not self.quitting:
            self.hide()
            event.ignore()
            if not self.settings.value('tray_hint_shown', False, type=bool):
                self.tray.showMessage('轻记仍在运行', '点击托盘图标即可继续记录；右键菜单可以退出。')
                self.settings.setValue('tray_hint_shown', True)
        else:
            self.reminders.stop()
            event.accept()
