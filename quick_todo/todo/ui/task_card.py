from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ..domain import Task


class TaskCard(QFrame):
    completed_changed = Signal(bool)
    important_changed = Signal(bool)
    edit_requested = Signal()
    delete_requested = Signal()

    def __init__(self, task: Task, parent=None):
        super().__init__(parent)
        self.setObjectName('taskCard')
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 13, 12, 13)
        row.setSpacing(12)
        self.checkbox = QCheckBox()
        self.checkbox.setAccessibleName('完成：' + task.title)
        self.checkbox.setToolTip('重新打开' if task.completed else '标记完成')
        self.checkbox.setChecked(task.completed)
        self.checkbox.toggled.connect(self.completed_changed.emit)
        row.addWidget(self.checkbox)
        content = QVBoxLayout()
        content.setSpacing(5)
        title = QLabel(task.title)
        title.setTextFormat(Qt.TextFormat.PlainText)
        title.setWordWrap(True)
        title.setObjectName('doneTitle' if task.completed else 'taskTitle')
        font = title.font()
        font.setStrikeOut(task.completed)
        title.setFont(font)
        content.addWidget(title)
        if task.notes:
            note = QLabel(task.notes.replace('\n', ' ')[:75])
            note.setTextFormat(Qt.TextFormat.PlainText)
            note.setWordWrap(True)
            note.setObjectName('muted')
            content.addWidget(note)
        if task.due:
            delta = (task.due - date.today()).days
            if task.completed:
                text = '截止 ' + task.due.isoformat()
            elif delta < 0:
                text = '已逾期 {} 天 · {}'.format(-delta, task.due.strftime('%m/%d'))
            elif delta == 0:
                text = '今天截止'
            elif delta == 1:
                text = '明天截止'
            else:
                text = '截止 ' + task.due.isoformat()
            due = QLabel(text)
            due.setObjectName('overdue' if delta < 0 and not task.completed else 'muted')
            content.addWidget(due)
        row.addLayout(content, 1)
        self.star_button = QPushButton('★' if task.important else '☆')
        self.star_button.setObjectName('star')
        self.star_button.setToolTip('取消重要标记' if task.important else '标为重要')
        self.star_button.setAccessibleName(self.star_button.toolTip())
        self.star_button.clicked.connect(lambda: self.important_changed.emit(not task.important))
        row.addWidget(self.star_button)
        self.edit_button = QPushButton('编辑')
        self.edit_button.setObjectName('icon')
        self.edit_button.clicked.connect(self.edit_requested.emit)
        row.addWidget(self.edit_button)
        self.delete_button = QPushButton('删除')
        self.delete_button.setObjectName('icon')
        self.delete_button.clicked.connect(self.delete_requested.emit)
        row.addWidget(self.delete_button)
