"""指定日期时间或每天固定时间的事件提醒管理。"""
import logging
from datetime import datetime, timedelta

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDateEdit, QDialog,
                               QDialogButtonBox, QFormLayout, QHeaderView,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QTimeEdit, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout)


class ScheduledReminderEditor(QDialog):
    def __init__(self, reminder=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('编辑定时提醒' if reminder else '新建定时提醒')
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setSpacing(12)
        self.title_input = QLineEdit(reminder.title if reminder else '')
        self.title_input.setMaxLength(200)
        self.title_input.setPlaceholderText('例如：关闭电脑')
        at = reminder.next_at if reminder else datetime.now() + timedelta(minutes=5)
        self.date_input = QDateEdit(QDate(at.year, at.month, at.day))
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat('yyyy-MM-dd')
        self.time_input = QTimeEdit(QTime(at.hour, at.minute))
        self.time_input.setDisplayFormat('HH:mm')
        self.daily = QCheckBox('每天在这个时间提醒')
        self.daily.setChecked(bool(reminder and reminder.daily))
        self.date_input.setEnabled(not self.daily.isChecked())
        self.daily.toggled.connect(lambda daily: self.date_input.setEnabled(not daily))
        form.addRow('提醒事件', self.title_input)
        form.addRow('日期', self.date_input)
        form.addRow('时间', self.time_input)
        form.addRow('', self.daily)
        layout.addLayout(form)
        hint = QLabel('不勾选“每天”时，只在所选日期提醒一次。\n'
                      '每天提醒按本机时间触发，今天已过则从明天开始。')
        hint.setObjectName('muted')
        layout.addWidget(hint)
        self.error = QLabel()
        self.error.setObjectName('overdue')
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('保存')
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName('primary')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        day, clock = self.date_input.date(), self.time_input.time()
        return dict(title=self.title_input.text(),
                    at=datetime(day.year(), day.month(), day.day(), clock.hour(), clock.minute()),
                    daily=self.daily.isChecked())

    def validate_and_accept(self):
        values = self.values()
        if not values['title'].strip():
            self.error.setText('请输入要提醒的事件。')
        elif not values['daily'] and values['at'] <= datetime.now():
            self.error.setText('提醒时间已经过去，请选择未来的日期和时间。')
        else:
            self.accept()


class ScheduledRemindersDialog(QDialog):
    def __init__(self, service, controller, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle('定时提醒')
        self.resize(670, 440)
        self.setMinimumSize(560, 350)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        top = QHBoxLayout()
        heading = QLabel('到点，提醒一件事')
        heading.setObjectName('emptyTitle')
        top.addWidget(heading)
        top.addStretch()
        self.add_button = QPushButton('＋ 新建提醒')
        self.add_button.setObjectName('primary')
        self.add_button.clicked.connect(lambda: self.edit_reminder())
        top.addWidget(self.add_button)
        layout.addLayout(top)
        hint = QLabel('例如：17:30 提醒关闭电脑，可设为单次或每天重复。\n'
                      '程序需保持运行，可隐藏到托盘；错过时间后恢复运行会补提醒一次。')
        hint.setObjectName('muted')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.items = QTreeWidget()
        self.items.setObjectName('scheduledList')
        self.items.setHeaderLabels(['事件', '提醒时间', '重复', '状态'])
        self.items.setRootIsDecorated(False)
        self.items.setAlternatingRowColors(True)
        self.items.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.items.header().setStretchLastSection(False)
        self.items.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            self.items.header().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.items.itemDoubleClicked.connect(lambda item, column: self.edit_selected())
        self.items.itemSelectionChanged.connect(self.update_actions)
        layout.addWidget(self.items, 1)
        self.empty = QLabel('还没有定时提醒，点击右上角“新建提醒”。')
        self.empty.setObjectName('muted')
        layout.addWidget(self.empty)
        bottom = QHBoxLayout()
        self.edit_button = QPushButton('编辑')
        self.edit_button.clicked.connect(self.edit_selected)
        bottom.addWidget(self.edit_button)
        self.delete_button = QPushButton('删除')
        self.delete_button.clicked.connect(self.delete_selected)
        bottom.addWidget(self.delete_button)
        bottom.addStretch()
        close = QPushButton('关闭')
        close.clicked.connect(self.accept)
        bottom.addWidget(close)
        layout.addLayout(bottom)
        controller.scheduled_fired.connect(self.refresh)
        self.refresh()

    def selected(self):
        item = self.items.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def update_actions(self):
        enabled = self.selected() is not None
        self.edit_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    def refresh(self):
        try:
            reminders = self.service.reminders()
        except Exception:
            logging.exception('读取定时提醒失败')
            self.empty.setText('读取失败，请检查数据目录后重新打开。')
            self.empty.show()
            return
        selected = self.selected()
        self.items.clear()
        for reminder in reminders:
            item = QTreeWidgetItem([reminder.title, reminder.next_at.strftime('%Y-%m-%d %H:%M'),
                                    '每天' if reminder.daily else '单次',
                                    '待提醒' if reminder.enabled else '已提醒'])
            item.setData(0, Qt.ItemDataRole.UserRole, reminder)
            item.setToolTip(0, reminder.title)
            self.items.addTopLevelItem(item)
            if selected and reminder.id == selected.id:
                self.items.setCurrentItem(item)
        self.empty.setText('还没有定时提醒，点击右上角“新建提醒”。')
        self.empty.setVisible(not reminders)
        self.update_actions()

    def edit_selected(self):
        reminder = self.selected()
        if reminder:
            self.edit_reminder(reminder)

    def edit_reminder(self, reminder=None):
        editor = ScheduledReminderEditor(reminder, self)
        while editor.exec() == QDialog.DialogCode.Accepted:
            try:
                self.service.save_reminder(**editor.values(), reminder=reminder)
            except ValueError as error:
                editor.error.setText(str(error))
            except Exception:
                logging.exception('保存定时提醒失败')
                editor.error.setText('保存失败，请检查数据目录权限和磁盘空间后重试。')
            else:
                self.refresh()
                break
        editor.deleteLater()

    def delete_selected(self):
        reminder = self.selected()
        if reminder:
            try:
                self.service.delete_reminder(reminder)
            except Exception:
                logging.exception('删除定时提醒失败')
                QMessageBox.warning(self, '删除失败', '未能删除，请检查数据目录后重试。')
                return
            self.refresh()
