"""随机待办与定时事件提醒：Qt 计时器和不抢焦点的桌面小窗。"""
import logging
import random
import time
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QDialogButtonBox,
                               QFormLayout, QFrame, QHBoxLayout, QLabel,
                               QPushButton, QSpinBox, QVBoxLayout)


class ReminderPopup(QFrame):
    open_requested = Signal()

    def __init__(self):
        # 独立顶层窗：主窗口隐藏到托盘时仍可显示。
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setObjectName('reminderPopup')
        self.setStyleSheet('QFrame#reminderPopup { background: #ffffff; '
                           'border: 1px solid #c6d0fa; border-radius: 12px; }')
        self.setWindowTitle('轻记 · 待办提醒')
        self.is_scheduled = False
        self.setFixedWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        header = QHBoxLayout()
        self.heading = QLabel('轻记 · 待办提醒')
        header.addWidget(self.heading)
        header.addStretch()
        close = QPushButton('×')
        close.setObjectName('icon')
        close.setAccessibleName('关闭提醒')
        close.clicked.connect(self.dismiss)
        header.addWidget(close)
        layout.addLayout(header)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        self.detail = QLabel()
        self.detail.setTextFormat(Qt.TextFormat.PlainText)
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)
        footer = QHBoxLayout()
        self.hint = QLabel()
        self.hint.setObjectName('muted')
        footer.addWidget(self.hint)
        footer.addStretch()
        self.open_button = QPushButton('查看待办')
        self.open_button.setObjectName('primary')
        self.open_button.clicked.connect(self.open_tasks)
        footer.addWidget(self.open_button)
        layout.addLayout(footer)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.hide_timer.timeout.connect(self.dismiss)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(100)
        self.countdown_timer.timeout.connect(self.update_countdown)

    def show_tasks(self, tasks, seconds):
        self.is_scheduled = False
        self.heading.setText('轻记 · 待办提醒')
        self.open_button.setText('查看待办')
        self.summary.setText('还有 {} 件待办未完成'.format(len(tasks)))
        titles = ['• ' + t.title.replace('\n', ' ')[:48] +
                  ('…' if len(t.title) > 48 else '') for t in tasks[:3]]
        self.detail.setText('\n'.join(titles))
        self.detail.setVisible(bool(tasks))
        self.show_for(seconds)

    def show_scheduled(self, reminder, seconds):
        self.is_scheduled = True
        self.heading.setText('轻记 · 定时提醒')
        self.summary.setText('提醒时间：' + reminder.next_at.strftime('%m月%d日 %H:%M'))
        self.detail.setText(reminder.title)
        self.detail.show()
        self.open_button.setText('知道了')
        self.show_for(seconds)

    def show_for(self, seconds):
        self.hint.setText('{} 秒后自动关闭'.format(seconds))
        self.adjustSize()
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()  # 避开任务栏，使用 Qt 的缩放坐标。
            self.move(max(area.left(), area.right() - self.width() - 15),
                      max(area.top(), area.bottom() - self.height() - 15))
        self.show()
        self.hide_timer.start(seconds * 1000)
        self.countdown_timer.start()

    def update_countdown(self):
        # 按关闭计时器的实际剩余时间显示，避免界面忙碌时逐秒递减产生漂移。
        remaining = self.hide_timer.remainingTime()
        if remaining <= 0:
            self.dismiss()
        else:
            self.hint.setText('{} 秒后自动关闭'.format((remaining + 999) // 1000))

    def dismiss(self):
        self.hide_timer.stop()
        self.countdown_timer.stop()
        self.hide()

    def open_tasks(self):
        self.dismiss()
        if not self.is_scheduled:
            self.open_requested.emit()


class ReminderController(QObject):
    scheduled_fired = Signal()

    def __init__(self, service, settings, parent):
        super().__init__(parent)
        self.service = service
        self.settings = settings
        self.popup = ReminderPopup()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.on_timeout)
        self.enabled = settings.value('reminders/enabled', True, type=bool)
        self.minimum = self.read_number('minimum_hours', 24, 1, 168)
        self.maximum = max(self.minimum, self.read_number('maximum_hours', 48, 1, 168))
        self.seconds = self.read_number('display_seconds', 6, 2, 30)
        self.destroyed.connect(self.popup.deleteLater)
        QApplication.instance().aboutToQuit.connect(self.stop)
        self.schedule(resume=True)
        self.scheduled_retry_at = 0
        self.scheduled_timer = QTimer(self)
        self.scheduled_timer.setInterval(1000)
        self.scheduled_timer.timeout.connect(self.check_scheduled)
        self.scheduled_timer.start()

    def check_scheduled(self):
        if self.popup.isVisible() or time.monotonic() < self.scheduled_retry_at:
            return
        try:
            reminder = self.service.take_due_reminder(datetime.now())
        except Exception:
            logging.exception('处理定时提醒失败，将稍后重试')
            self.scheduled_retry_at = time.monotonic() + 60
            return
        if reminder:
            self.popup.show_scheduled(reminder, self.seconds)
            self.scheduled_fired.emit()

    def read_number(self, key, default, lower, upper):
        try:
            return max(lower, min(upper, int(self.settings.value('reminders/' + key, default))))
        except (TypeError, ValueError):
            return default

    def schedule(self, resume=False):
        self.timer.stop()
        if self.enabled:
            now = time.time()
            try:
                saved = float(self.settings.value('reminders/next_due_at', 0)) if resume else 0
            except (ValueError, TypeError):
                saved = 0
            # 关机期间已到期时，在启动后检查一次；不连续补发旧提醒。
            self.next_due_at = saved if 0 < saved <= now + self.maximum * 3600 else (
                now + random.randint(self.minimum * 3600, self.maximum * 3600))
            self.settings.setValue('reminders/next_due_at', self.next_due_at)
            self.settings.sync()
            self.arm_timer()

    def arm_timer(self):
        # 定期核对绝对时间，以兼容电脑休眠、恢复和系统时钟调整。
        self.timer.start(max(1000, min(60000, int((self.next_due_at - time.time()) * 1000))))

    def on_timeout(self):
        if not self.enabled:
            return
        if time.time() < self.next_due_at:
            self.arm_timer()
            return
        try:
            if self.enabled and QApplication.activeModalWidget() is None:
                self.show_now()
        finally:
            self.schedule()

    def show_now(self):
        # 固定时间的事件优先，同一时间多个事件逐个显示，避免小窗互相覆盖。
        self.check_scheduled()
        if self.popup.isVisible():
            return
        try:
            tasks = self.service.select(self.service.all(), 'inbox')
        except Exception:
            logging.exception('读取提醒待办失败')
            self.popup.dismiss()
            return
        if tasks:
            self.popup.show_tasks(tasks, self.seconds)
        else:
            self.popup.dismiss()

    def configure(self, enabled, minimum, maximum, seconds):
        self.enabled, self.minimum, self.maximum, self.seconds = enabled, minimum, maximum, seconds
        for key, value in [('enabled', enabled), ('minimum_hours', minimum),
                           ('maximum_hours', maximum), ('display_seconds', seconds)]:
            self.settings.setValue('reminders/' + key, value)
        self.settings.remove('reminders/next_due_at')
        self.settings.sync()
        if not self.popup.is_scheduled:
            self.popup.dismiss()
        self.schedule()

    def stop(self):
        self.timer.stop()
        self.scheduled_timer.stop()
        self.popup.dismiss()


class ReminderSettings(QDialog):
    def __init__(self, controller, parent):
        super().__init__(parent)
        self.setWindowTitle('提醒设置')
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        self.enabled = QCheckBox('随机提醒未完成的待办')
        self.enabled.setChecked(controller.enabled)
        layout.addWidget(self.enabled)
        form = QFormLayout()
        self.minimum = QSpinBox()
        self.maximum = QSpinBox()
        self.seconds = QSpinBox()
        for widget, value in [(self.minimum, controller.minimum), (self.maximum, controller.maximum)]:
            widget.setRange(1, 168)
            widget.setSuffix(' 小时')
            widget.setValue(value)
        self.seconds.setRange(2, 30)
        self.seconds.setSuffix(' 秒')
        self.seconds.setValue(controller.seconds)
        form.addRow('最短间隔', self.minimum)
        form.addRow('最长间隔', self.maximum)
        form.addRow('小窗显示', self.seconds)
        layout.addLayout(form)
        hint = QLabel('默认随机间隔 24～48 小时，不固定在某个钟点。\n'
                      '重启后保留下次提醒时间，已到期则检查一次。\n'
                      '右下角小窗自动关闭；隐藏到托盘后仍会提醒。\n'
                      '全部完成后不再随机提醒；定时事件仍正常提醒。\n'
                      '小窗显示时长也适用于定时提醒。')
        hint.setObjectName('muted')
        layout.addWidget(hint)
        self.error = QLabel()
        self.error.setObjectName('overdue')
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('保存')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        preview = buttons.addButton('试试看', QDialogButtonBox.ButtonRole.ActionRole)
        preview.setToolTip('按已保存的显示时长提醒一次，不改变下次自动提醒时间')
        preview.clicked.connect(controller.show_now)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate_and_accept(self):
        if self.minimum.value() > self.maximum.value():
            self.error.setText('最长间隔不能小于最短间隔。')
            return
        self.accept()

    def values(self):
        return self.enabled.isChecked(), self.minimum.value(), self.maximum.value(), self.seconds.value()
