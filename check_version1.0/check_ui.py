# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'check.ui'
##
## Created by: Qt User Interface Compiler version 6.6.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QGroupBox, QHBoxLayout,
    QLabel, QMainWindow, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpacerItem, QStatusBar, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(980, 730)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.mainLayout = QVBoxLayout(self.centralwidget)
        self.mainLayout.setSpacing(14)
        self.mainLayout.setObjectName(u"mainLayout")
        self.mainLayout.setContentsMargins(22, 20, 22, 20)
        self.languageLayout = QHBoxLayout()
        self.languageLayout.setObjectName(u"languageLayout")
        self.titleLabel = QLabel(self.centralwidget)
        self.titleLabel.setObjectName(u"titleLabel")

        self.languageLayout.addWidget(self.titleLabel)

        self.languageSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.languageLayout.addItem(self.languageSpacer)

        self.languageLabel = QLabel(self.centralwidget)
        self.languageLabel.setObjectName(u"languageLabel")

        self.languageLayout.addWidget(self.languageLabel)

        self.languageComboBox = QComboBox(self.centralwidget)
        self.languageComboBox.addItem("")
        self.languageComboBox.addItem("")
        self.languageComboBox.setObjectName(u"languageComboBox")
        self.languageComboBox.setMinimumSize(QSize(130, 38))

        self.languageLayout.addWidget(self.languageComboBox)


        self.mainLayout.addLayout(self.languageLayout)

        self.readerGroupBox = QGroupBox(self.centralwidget)
        self.readerGroupBox.setObjectName(u"readerGroupBox")
        self.readerLayout = QHBoxLayout(self.readerGroupBox)
        self.readerLayout.setObjectName(u"readerLayout")
        self.readerLayout.setContentsMargins(16, 18, 16, 14)
        self.readerLabel = QLabel(self.readerGroupBox)
        self.readerLabel.setObjectName(u"readerLabel")

        self.readerLayout.addWidget(self.readerLabel)

        self.readerComboBox = QComboBox(self.readerGroupBox)
        self.readerComboBox.setObjectName(u"readerComboBox")
        self.readerComboBox.setMinimumSize(QSize(430, 38))

        self.readerLayout.addWidget(self.readerComboBox)

        self.refreshButton = QPushButton(self.readerGroupBox)
        self.refreshButton.setObjectName(u"refreshButton")
        self.refreshButton.setMinimumSize(QSize(150, 38))

        self.readerLayout.addWidget(self.refreshButton)


        self.mainLayout.addWidget(self.readerGroupBox)

        self.checkGroupBox = QGroupBox(self.centralwidget)
        self.checkGroupBox.setObjectName(u"checkGroupBox")
        self.checkLayout = QHBoxLayout(self.checkGroupBox)
        self.checkLayout.setObjectName(u"checkLayout")
        self.checkLayout.setContentsMargins(16, 18, 16, 14)
        self.checkCplcButton = QPushButton(self.checkGroupBox)
        self.checkCplcButton.setObjectName(u"checkCplcButton")
        self.checkCplcButton.setMinimumSize(QSize(170, 42))

        self.checkLayout.addWidget(self.checkCplcButton)

        self.checkDeButton = QPushButton(self.checkGroupBox)
        self.checkDeButton.setObjectName(u"checkDeButton")
        self.checkDeButton.setMinimumSize(QSize(170, 42))

        self.checkLayout.addWidget(self.checkDeButton)

        self.statusTextLabel = QLabel(self.checkGroupBox)
        self.statusTextLabel.setObjectName(u"statusTextLabel")
        self.statusTextLabel.setMinimumSize(QSize(90, 24))
        self.statusTextLabel.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.checkLayout.addWidget(self.statusTextLabel)

        self.resultIconLabel = QLabel(self.checkGroupBox)
        self.resultIconLabel.setObjectName(u"resultIconLabel")
        self.resultIconLabel.setMinimumSize(QSize(72, 72))
        self.resultIconLabel.setMaximumSize(QSize(72, 72))
        self.resultIconLabel.setAlignment(Qt.AlignCenter)

        self.checkLayout.addWidget(self.resultIconLabel)


        self.mainLayout.addWidget(self.checkGroupBox)

        self.logGroupBox = QGroupBox(self.centralwidget)
        self.logGroupBox.setObjectName(u"logGroupBox")
        self.logLayout = QVBoxLayout(self.logGroupBox)
        self.logLayout.setObjectName(u"logLayout")
        self.logLayout.setContentsMargins(12, 18, 12, 12)
        self.clearLogButton = QPushButton(self.logGroupBox)
        self.clearLogButton.setObjectName(u"clearLogButton")
        self.clearLogButton.setMinimumSize(QSize(110, 36))

        self.logLayout.addWidget(self.clearLogButton, 0, Qt.AlignRight)

        self.logTextEdit = QPlainTextEdit(self.logGroupBox)
        self.logTextEdit.setObjectName(u"logTextEdit")
        self.logTextEdit.setMinimumSize(QSize(0, 300))
        self.logTextEdit.setUndoRedoEnabled(False)

        self.logLayout.addWidget(self.logTextEdit)


        self.mainLayout.addWidget(self.logGroupBox)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Version verification tool", None))
        self.titleLabel.setText(QCoreApplication.translate("MainWindow", u"\u5361\u7247\u6821\u9a8c", None))
        self.languageLabel.setText(QCoreApplication.translate("MainWindow", u"\u8bed\u8a00 / Language", None))
        self.languageComboBox.setItemText(0, QCoreApplication.translate("MainWindow", u"\u4e2d\u6587", None))
        self.languageComboBox.setItemText(1, QCoreApplication.translate("MainWindow", u"English", None))

        self.readerGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u8bfb\u5361\u5668\u8fde\u63a5", None))
        self.readerLabel.setText(QCoreApplication.translate("MainWindow", u"\u8bfb\u5361\u5668\uff1a", None))
        self.readerComboBox.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u8bf7\u5237\u65b0\u5e76\u9009\u62e9\u8bfb\u5361\u5668", None))
        self.refreshButton.setText(QCoreApplication.translate("MainWindow", u"\u5237\u65b0\u8bfb\u5361\u5668", None))
        self.checkGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u7248\u672c\u6821\u9a8c", None))
        self.checkCplcButton.setText(QCoreApplication.translate("MainWindow", u"\u6821\u9a8c CPLC", None))
        self.checkDeButton.setText(QCoreApplication.translate("MainWindow", u"\u6821\u9a8c DE", None))
        self.statusTextLabel.setText(QCoreApplication.translate("MainWindow", u"\u7b49\u5f85\u6821\u9a8c", None))
        self.logGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u8fd0\u884c\u65e5\u5fd7", None))
        self.clearLogButton.setText(QCoreApplication.translate("MainWindow", u"\u6e05\u7a7a\u65e5\u5fd7", None))
#if QT_CONFIG(tooltip)
        self.clearLogButton.setToolTip(QCoreApplication.translate("MainWindow", u"\u6e05\u7a7a\u5f53\u524d\u663e\u793a\u7684\u8fd0\u884c\u65e5\u5fd7", None))
#endif // QT_CONFIG(tooltip)
    # retranslateUi

