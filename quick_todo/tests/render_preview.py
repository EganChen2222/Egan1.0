"""用临时数据渲染真实 Qt 界面；不修改用户数据库。"""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from todo.service import TaskService
from todo.storage import SQLiteTaskRepository
from todo.ui.editor import TaskEditor
from todo.ui.icons import application_icon
from todo.ui.theme import STYLE
from todo.ui.window import MainWindow


def main():
    app = QApplication([])
    # Windows 的 Qt offscreen 插件没有系统字体库，需要显式加载用于截图。
    fonts = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    for name in ('msyh.ttc', 'msyhbd.ttc', 'seguisym.ttf'):
        if (fonts / name).exists():
            QFontDatabase.addApplicationFont(str(fonts / name))
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    output = ROOT / 'docs'
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        repo = SQLiteTaskRepository(root / 'tasks.sqlite3')
        service = TaskService(repo)
        first = service.add('整理本周的工作计划', '先把最重要的三件事写下来', date.today(), True)
        service.add('把突然想到的好点子记下来', '不用急着完成，先给想法一个落脚的地方')
        service.add('读完那篇收藏的文章', due=date.today() + timedelta(days=1))
        service.add('给自己留半小时散步', '放下手机，出去走走')
        done = service.add('开始使用轻记')
        service.complete(done, True)
        window = MainWindow(service, QSettings(str(root / 'settings.ini'), QSettings.IniFormat),
                            application_icon(ROOT / 'assets/icons'), False)
        window.show()
        app.processEvents()
        window.grab().save(str(output / 'preview.png'))
        window.resize(760, 520)
        app.processEvents()
        window.grab().save(str(output / 'preview-small.png'))
        window.change_view('today')
        window.search.setText('不存在')
        app.processEvents()
        window.grab().save(str(output / 'preview-empty.png'))
        editor = TaskEditor(first, window)
        editor.show()
        app.processEvents()
        editor.grab().save(str(output / 'preview-editor.png'))
        editor.close()
        window.close()
        repo.close()
    print('Rendered four Qt interface states into docs/.')


if __name__ == '__main__':
    main()
