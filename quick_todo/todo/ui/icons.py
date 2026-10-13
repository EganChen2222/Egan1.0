from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


def application_icon(assets: Path) -> QIcon:
    for name in ('app.ico', 'app.png', 'app.svg'):
        path = assets / name
        if path.is_file():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#506bda'))
    painter.drawRoundedRect(QRectF(2, 2, 60, 60), 17, 17)
    painter.setPen(QPen(QColor('white'), 5, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawLine(18, 33, 28, 43)
    painter.drawLine(28, 43, 46, 22)
    painter.end()
    return QIcon(pixmap)
