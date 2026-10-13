# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QApplication

try:
    from .main_window import CheckWindow
except ImportError:
    from main_window import CheckWindow


def main():

    app = QApplication([])
    window = CheckWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    main()
