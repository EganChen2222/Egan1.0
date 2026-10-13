STYLE = """
QWidget { font-family: 'Microsoft YaHei UI', 'Microsoft YaHei', sans-serif;
          font-size: 14px; color: #26364b; }
QMainWindow, QDialog { background: #f6f8fc; }
QFrame#sidebar { background: #edf1f9; border: none; border-radius: 16px; }
QLabel#brand { font-size: 24px; font-weight: 700; color: #344fbe; }
QLabel#heading { font-size: 28px; font-weight: 700; }
QLabel#muted { color: #7b8799; font-size: 12px; }
QLabel#emptyTitle { font-size: 20px; font-weight: 600; color: #667893; }
QLabel#emptyIcon { font-size: 42px; color: #8094de; }
QPushButton { background: #ffffff; border: 1px solid #e2e7f0;
              border-radius: 9px; padding: 9px 14px; }
QPushButton:hover { background: #edf1ff; border-color: #c6d0fa; }
QPushButton:pressed { background: #dee6ff; }
QPushButton:focus { border-color: #6b82df; }
QPushButton#nav { text-align: left; background: transparent; border: none;
                 padding: 13px 16px; font-weight: 600; }
QPushButton#nav:checked { background: #dde5fc; color: #3456c5; }
QPushButton#nav:hover { background: #e3e9f6; }
QPushButton#primary { background: #506bda; color: white; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #405bc8; }
QPushButton#reminderSettings { background: #edf1ff; color: #3456c5;
                              border-color: #c6d0fa; font-weight: 600; }
QPushButton#reminderSettings:hover { background: #dde5fc; border-color: #6b82df; }
QPushButton#icon { padding: 5px 9px; background: transparent; border: none; color: #78869b; }
QPushButton#icon:hover { background: #e9eefb; color: #3859ba; }
QPushButton#star { padding: 5px 8px; font-size: 23px; background: transparent; border: none; color: #c28a30; }
QLineEdit, QTextEdit, QDateEdit, QTimeEdit { background: white; border: 1px solid #dfe5ef;
                               border-radius: 9px; padding: 10px; selection-background-color: #5877df; }
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QTimeEdit:focus { border-color: #6b82df; }
QLineEdit#capture { font-size: 15px; padding: 15px; }
QFrame#taskCard { background: white; border: 1px solid #e6eaf2; border-radius: 12px; }
QLabel#taskTitle { font-size: 15px; }
QLabel#doneTitle { font-size: 15px; color: #8f9aad; }
QLabel#overdue { color: #bb6352; font-size: 12px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 19px; height: 19px; }
QScrollArea { background: transparent; border: none; }
QWidget#taskList { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #ced6e5; border-radius: 4px; min-height: 35px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QToolTip { background: #26364b; color: white; border: none; padding: 6px; }
QTreeWidget#scheduledList { background: white; alternate-background-color: #f6f8fc;
                           border: 1px solid #e6eaf2; border-radius: 9px; }
QTreeWidget#scheduledList::item { padding: 8px; }
QTreeWidget#scheduledList::item:selected { background: #dde5fc; color: #26364b; }
QTreeWidget#scheduledList QHeaderView::section { background: #edf1f9; color: #667893;
    border: none; border-bottom: 1px solid #e6eaf2; padding: 8px; }
"""
