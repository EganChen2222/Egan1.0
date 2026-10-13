from datetime import date
from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (QCheckBox, QDateEdit, QDialog, QDialogButtonBox,
                               QFormLayout, QLabel, QLineEdit, QTextEdit, QVBoxLayout)

from ..domain import Task


class TaskEditor(QDialog):
    def __init__(self, task: Optional[Task] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('编辑待办' if task else '新建待办')
        self.resize(470, 420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setSpacing(14)
        self.title_input = QLineEdit(task.title if task else '')
        self.title_input.setMaxLength(200)
        self.title_input.setPlaceholderText('要做什么？')
        self.notes_input = QTextEdit()
        self.notes_input.setAcceptRichText(False)
        self.notes_input.setPlaceholderText('补充细节、链接或下一步…')
        self.notes_input.setPlainText(task.notes if task else '')
        self.has_due = QCheckBox('设置截止日期')
        self.has_due.setChecked(bool(task and task.due))
        self.due_input = QDateEdit()
        self.due_input.setCalendarPopup(True)
        self.due_input.setDisplayFormat('yyyy-MM-dd')
        due = task.due if task and task.due else date.today()
        self.due_input.setDate(QDate(due.year, due.month, due.day))
        self.due_input.setEnabled(self.has_due.isChecked())
        self.has_due.toggled.connect(self.due_input.setEnabled)
        self.important_input = QCheckBox('标为重要')
        self.important_input.setChecked(bool(task and task.important))
        form.addRow('事项', self.title_input)
        form.addRow('备注', self.notes_input)
        form.addRow('', self.has_due)
        form.addRow('截止', self.due_input)
        form.addRow('', self.important_input)
        layout.addLayout(form)
        self.error = QLabel()
        self.error.setObjectName('overdue')
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('保存')
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName('primary')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.title_input.setFocus()

    def validate_and_accept(self):
        if not self.title_input.text().strip():
            self.error.setText('请先写下要做的事情。')
            self.title_input.setFocus()
        elif len(self.notes_input.toPlainText()) > 10000:
            self.error.setText('备注最多 10000 个字。')
        else:
            self.accept()

    def values(self):
        qdate = self.due_input.date()
        due = date(qdate.year(), qdate.month(), qdate.day()) if self.has_due.isChecked() else None
        return dict(title=self.title_input.text(), notes=self.notes_input.toPlainText(),
                    due=due, important=self.important_input.isChecked())
