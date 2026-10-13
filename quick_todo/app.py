"""组合入口：在此选择存储实现并注入业务层和界面。"""
import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QSettings, QTimer, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from todo.service import TaskService
from todo.global_hotkey import GlobalQuickCapture, request_foreground
from todo.storage import SQLiteTaskRepository
from todo.ui.icons import application_icon
from todo.ui.theme import STYLE
from todo.ui.window import MainWindow


def main():
    parser = argparse.ArgumentParser(description='轻记 · 独立的本地待办工具')
    parser.add_argument('--data-dir', type=Path, help='自定义数据目录')
    parser.add_argument('--smoke-test', action='store_true', help='无托盘启动并自动退出，验证启动链路')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    data_dir = (args.data_dir or root / 'data').resolve()
    app = QApplication(sys.argv[:1])
    app.setApplicationName('QuickTodo')
    app.setOrganizationName('QuickTodo')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    icon = application_icon(root / 'assets' / 'icons')
    app.setWindowIcon(icon)
    repository = None
    lock = None
    hotkey = None
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(data_dir / 'app.lock'))
        lock.setStaleLockTime(0)
        if not lock.tryLock(100):
            QMessageBox.information(None, '轻记', '轻记已经运行，或数据目录无法写入。\n请先从系统托盘打开已有窗口。')
            return 1
        logging.basicConfig(
            handlers=[logging.FileHandler(str(data_dir / 'app.log'), encoding='utf-8')],
            level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s')
        repository = SQLiteTaskRepository(data_dir / 'tasks.sqlite3')
        # 在进入事件循环前验证数据可读；损坏时不会用空库覆盖原文件。
        repository.all()
        settings = QSettings(str(data_dir / 'settings.ini'), QSettings.Format.IniFormat)
        window = MainWindow(TaskService(repository), settings, icon, enable_tray=not args.smoke_test)
        window.show()
        window.capture.setFocus()
        app.aboutToQuit.connect(window.save_settings)
        if args.smoke_test:
            QTimer.singleShot(350, app.quit)
        else:
            window.foreground_request = request_foreground
            hotkey = GlobalQuickCapture(app)
            hotkey.activated.connect(window.wake_for_capture, Qt.ConnectionType.QueuedConnection)
            hotkey.status_changed.connect(window.set_hotkey_status, Qt.ConnectionType.QueuedConnection)
            app.aboutToQuit.connect(hotkey.stop)
            hotkey.start()
        return app.exec()
    except Exception as error:
        logging.exception('启动失败')
        QMessageBox.critical(None, '无法启动轻记', '请检查数据目录是否可写或数据库是否损坏。\n{}\n\n{}'.format(data_dir, error))
        return 1
    finally:
        if hotkey:
            hotkey.stop()
        if repository:
            repository.close()
        if lock and lock.isLocked():
            lock.unlock()


if __name__ == '__main__':
    sys.exit(main())
