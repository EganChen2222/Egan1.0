# -*- coding: utf-8 -*-
"""Qt 展示层：仅处理界面事件和日志展示，不包含读卡器通信实现。"""

import os

from PySide6.QtCore import QSettings, QSize, Qt, Slot
from PySide6.QtGui import QIcon, QPixmap, QTextCursor
from PySide6.QtWidgets import QMainWindow

try:
    from .card_service import CardService, CardServiceError, CommandResult
    from .check_ui import Ui_MainWindow
    from .translations import translate
except ImportError:
    from card_service import CardService, CardServiceError, CommandResult
    from check_ui import Ui_MainWindow
    from translations import translate


class CheckWindow(QMainWindow):
    ASSET_DIR = os.path.join(os.path.dirname(__file__), "config", "logo")
    CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config", "version.ini")

    def __init__(self, parent=None):
        """创建窗口、加载 UI，并初始化读卡器服务和读卡器列表。"""
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon(os.path.join(self.ASSET_DIR, "app-icon.ico")))
        self.service = CardService()
        self.reader_list = []
        self.settings = QSettings("Egan", "VersionVerificationTool")
        saved_language = self.settings.value("ui/language", "zh")
        self.language = saved_language if saved_language in ("zh", "en") else "zh"
        self.result_status = None
        self.result_kind = None
        self.init_ui()
        self.refresh_readers()

    def init_ui(self):
        """配置界面样式、控件信号、按钮图标和初始校验状态。"""
        self.setStyleSheet("""
            QMainWindow { background: #f5f7fa; }
            QGroupBox { background: #ffffff; border: 1px solid #d8e0ea; border-radius: 8px; margin-top: 12px; padding-top: 8px; font-size: 15px; font-weight: 700; color: #263548; }
            QGroupBox::title { left: 14px; padding: 0 5px; }
            QLabel { font-size: 14px; font-weight: 600; color: #334155; }
            QComboBox { min-height: 32px; padding: 0 8px; border: 1px solid #cbd5e1; border-radius: 5px; background: white; }
            QPushButton { min-height: 32px; padding: 4px 12px; border: 0; border-radius: 5px; background: #1677ff; color: white; font-weight: 600; }
            QPushButton:hover { background: #4096ff; }
            QPushButton:pressed { background: #0958d9; }
            QPushButton#clearLogButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
            QPushButton#clearLogButton:hover { background: #e2e8f0; color: #1e293b; }
            QPushButton#clearLogButton:pressed { background: #cbd5e1; }
            QPlainTextEdit { background: #151b23; color: #d7e2f0; border: 1px solid #c8d2dc; font-family: Consolas, "Microsoft YaHei UI"; font-size: 13px; }
        """)
        self.ui.readerComboBox.currentIndexChanged.connect(self.reader_selected)
        self.ui.refreshButton.clicked.connect(self.refresh_readers)
        self.ui.checkDeButton.clicked.connect(self.check_version)
        self.ui.checkCplcButton.clicked.connect(self.check_cplc)
        self.ui.languageComboBox.setCurrentIndex(1 if self.language == "en" else 0)
        self.ui.languageComboBox.currentIndexChanged.connect(self.change_language)
        self.ui.clearLogButton.clicked.connect(self.ui.logTextEdit.clear)
        self.ui.logTextEdit.setReadOnly(True)
        self.ui.refreshButton.setIcon(QIcon(os.path.join(self.ASSET_DIR, "refresh.png")))
        for button in (self.ui.checkDeButton, self.ui.checkCplcButton):
            button.setIcon(QIcon(os.path.join(self.ASSET_DIR, "start.png")))
            button.setIconSize(QSize(20, 20))
        self.ui.refreshButton.setIconSize(QSize(20, 20))
        self.apply_language()

    def tr_text(self, message_key, **params):
        """按当前语言取得文案，并填入读卡器、状态字等动态内容。"""
        return translate(message_key, self.language, **params)

    @Slot(int)
    def change_language(self, index):
        self.language = "en" if index == 1 else "zh"
        self.apply_language()
        self.settings.setValue("ui/language", self.language)
        self.settings.sync()

    def apply_language(self):
        self.ui.languageLabel.setText(self.tr_text("language_label"))
        self.ui.languageComboBox.setItemText(0, self.tr_text("language_chinese"))
        self.ui.languageComboBox.setItemText(1, self.tr_text("language_english"))
        self.setWindowTitle(self.tr_text("window_title"))
        self.ui.titleLabel.setText(self.tr_text("card_verification"))
        self.ui.titleLabel.setStyleSheet("font-size: 22px; font-weight: 700; color: #1e293b;")
        self.ui.readerGroupBox.setTitle(self.tr_text("reader_connection"))
        self.ui.readerLabel.setText(self.tr_text("reader_label"))
        self.ui.readerComboBox.setPlaceholderText(self.tr_text("reader_placeholder"))
        self.ui.refreshButton.setText(self.tr_text("refresh_readers"))
        self.ui.checkGroupBox.setTitle(self.tr_text("card_verification"))
        self.ui.checkDeButton.setText(self.tr_text("verify_de"))
        self.ui.checkCplcButton.setText(self.tr_text("verify_cplc"))
        self.ui.checkCplcButton.setToolTip(self.tr_text("cplc_hint"))
        self.ui.checkDeButton.setToolTip(self.tr_text("de_hint"))
        self.ui.logGroupBox.setTitle(self.tr_text("activity_log"))
        self.ui.clearLogButton.setText(self.tr_text("clear_log"))
        self.ui.clearLogButton.setToolTip(self.tr_text("clear_log_hint"))
        self.set_result_status(self.result_status)

    def set_result_status(self, success):
        self.result_status = success
        if success is None:
            filename, text, color = "pending.png", self.tr_text("status_ready"), "#64748b"
        elif success:
            filename, text, color = "success.png", self.tr_text("status_passed"), "#16a34a"
        else:
            filename, text, color = "fail.png", self.tr_text("status_failed"), "#dc2626"
        if self.result_kind:
            text = f"{self.result_kind} · {text}"
        pixmap = QPixmap(os.path.join(self.ASSET_DIR, filename))
        self.ui.resultIconLabel.setPixmap(pixmap.scaled(self.ui.resultIconLabel.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.ui.resultIconLabel.setToolTip(text)
        self.ui.statusTextLabel.setText(text)
        self.ui.statusTextLabel.setStyleSheet(f"color: {color};")

    def log(self, message):
        """向只读日志框追加一条消息，并自动滚动到末尾。"""
        self.ui.logTextEdit.appendPlainText(message)
        self.ui.logTextEdit.moveCursor(QTextCursor.MoveOperation.End)

    def log_exchange(self, result: CommandResult):
        """将一次业务命令包含的所有 APDU 收发记录逐条打印到日志框。"""
        for exchange in result.exchanges:
            self.log(f">>> APDU : {exchange.command}")
            self.log(f"<<< RESP : {exchange.response or self.tr_text('no_response')}")
            self.log(f"<<< SW   : {exchange.status_word}")

    def log_success(self, message):
        self.log("\n============================================================")
        self.log(f"                 ✓ {message}")
        self.log("============================================================\n")
        self.set_result_status(True)

    def log_error(self, message):
        self.log("\n############################################################")
        self.log(f"                 ✗ {message}")
        self.log("############################################################\n")
        self.set_result_status(False)

    @Slot()
    def refresh_readers(self):
        """刷新读卡器；日志显示检测到卡片的接口，并自动选中其读卡器。"""
        # 刷新后的卡片和读卡器状态可能已变化，清除上一次校验结果。
        self.result_kind = None
        self.set_result_status(None)
        self.log("\n" + "-" * 60 + "\n" + self.tr_text("scanning_readers") + "\n" + "-" * 60)
        selected_reader = self.ui.readerComboBox.currentData()
        selected_name = str(selected_reader) if selected_reader is not None else ""
        self.service.disconnect()
        try:
            self.reader_list = self.service.list_readers()
        except CardServiceError as error:
            self.reader_list = []
            self.ui.readerComboBox.blockSignals(True)
            self.ui.readerComboBox.clear()
            self.ui.readerComboBox.blockSignals(False)
            self.log_error(self.tr_text("list_readers_failed") + error.localized(self.language))
            return

        if not self.reader_list:
            self.ui.readerComboBox.blockSignals(True)
            self.ui.readerComboBox.clear()
            self.ui.readerComboBox.blockSignals(False)
            self.log(self.tr_text("no_readers"))
            return

        card_atrs = {
            str(reader): atr for reader, atr in self.service.find_readers_with_card(self.reader_list)
        }

        self.ui.readerComboBox.blockSignals(True)
        self.ui.readerComboBox.clear()
        for reader in self.reader_list:
            self.ui.readerComboBox.addItem(str(reader), reader)
        # 若有卡，优先选中第一个检测到卡的读卡器；否则保留原选择。
        target_index = next(
            (index for index, reader in enumerate(self.reader_list) if str(reader) in card_atrs),
            next(
                (index for index, reader in enumerate(self.reader_list) if str(reader) == selected_name),
                0,
            ),
        )
        self.ui.readerComboBox.setCurrentIndex(target_index)
        self.ui.readerComboBox.blockSignals(False)

        self.log(self.tr_text("readers_detected", count=len(self.reader_list)))
        for index, reader in enumerate(self.reader_list, start=1):
            atr = card_atrs.get(str(reader))
            if atr:
                self.log(f"  [{index}] {reader}  - " + self.tr_text("card_detected") + atr)
            else:
                self.log(f"  [{index}] {reader}")

    @Slot(int)
    def reader_selected(self, index):
        """响应下拉框选择：连接对应读卡器中的卡片并在日志打印 ATR。"""
        if not 0 <= index < len(self.reader_list):
            return
        reader = self.reader_list[index]
        self.result_kind = None
        self.set_result_status(None)
        self.log("\n" + "=" * 60 + "\n" + self.tr_text("connecting_reader", reader=reader))
        try:
            atr = self.service.connect(reader)
            self.log(self.tr_text("reader_connected"))
            self.log(f"ATR : {atr}")
        except CardServiceError as error:
            # 无卡不影响列表刷新；仅记录状态，等待插卡并重新选择即可。
            self.log(self.tr_text("card_connection_failed") + error.localized(self.language))

    @Slot()
    def check_version(self):
        """保留 DE 校验入口。"""
        self.verify_card("DE")

    @Slot()
    def check_cplc(self):
        self.verify_card("CPLC")

    def verify_card(self, kind):
        """两个入口共用连接流程，分别读取并按各自规则比对。"""
        self.result_kind = kind
        self.set_result_status(None)
        self.log("\n" + "=" * 60)
        self.log(self.tr_text("verification_started", kind=kind))
        self.log("=" * 60)
        try:
            reader_index = self.ui.readerComboBox.currentIndex()
            if not 0 <= reader_index < len(self.reader_list):
                self.log_error(self.tr_text("no_valid_reader"))
                return
            reader = self.reader_list[reader_index]
            atr = self.service.connect(reader)
            self.log(self.tr_text("current_reader", reader=reader))
            self.log(f"ATR : {atr}")

            self.log(self.tr_text("initialize_card"))
            select_result = self.service.select_isd()
            self.log_exchange(select_result)
            if select_result.status_word != "9000":
                self.log_error(self.tr_text("initialize_failed", status_word=select_result.status_word))
                return

            self.log(self.tr_text("read_card", kind=kind))
            result = self.service.read_cplc() if kind == "CPLC" else self.service.read_de()
            self.log_exchange(result)
            if result.status_word != "9000":
                self.log_error(self.tr_text("read_failed", kind=kind, status_word=result.status_word))
                return
            raw_value = result.response.replace(" ", "").upper()
            if kind == "CPLC":
                value = self.service.parse_cplc_value(result.response)
                comparison_value = value[:12]
                section, byte_length = "CPLC", 6
            else:
                value = self.service.parse_de_value(result.response)
                comparison_value = value
                section, byte_length = "Version", None
            self.log(self.tr_text("raw_response", kind=kind, raw_value=raw_value))
            self.log(self.tr_text("card_value", kind=kind, value=value))
            if kind == "CPLC":
                self.log(self.tr_text("cplc_prefix", comparison_value=comparison_value))

            self.log(self.tr_text("load_settings"))
            versions, invalid_entries = self.service.load_versions(self.CONFIG_FILE, section, byte_length)
            for key, _ in invalid_entries:
                rule = self.tr_text("cplc_format_rule") if kind == "CPLC" else self.tr_text("de_format_rule")
                self.log(self.tr_text("invalid_setting", key=key, rule=rule))
            if not versions:
                self.log_error(self.tr_text("no_valid_values", section=section, kind=kind))
                return
            self.log(self.tr_text("compare_card", kind=kind))
            matched = comparison_value in versions or (kind == "DE" and raw_value in versions)
            if matched:
                self.log_success(self.tr_text("verification_passed", kind=kind, comparison_value=comparison_value))
            else:
                self.log_error(self.tr_text("verification_failed", kind=kind, comparison_value=comparison_value))
        except CardServiceError as error:
            self.log_error(error.localized(self.language))

    def closeEvent(self, event):
        """窗口关闭前断开卡片连接，释放读卡器占用。"""
        self.service.disconnect()
        event.accept()
