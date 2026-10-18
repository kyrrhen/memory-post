from __future__ import annotations

import math
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtCore import (
    QEasingCurve, QEvent, QObject, QPoint, QPointF, QPropertyAnimation,
    QRect, QRectF, QSize, Qt, QThread, QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QImageReader, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox,
    QFileDialog, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QProgressBar,
    QPushButton, QSizeGrip, QSpinBox, QStackedWidget, QTextEdit, QVBoxLayout,
    QWidget,
)

from sender import build_bundle, compute_target_size
from receiver import reconstruct_bundle

APP_NAME = "记忆邮局"
APP_VERSION = "1.1.0"
APP_TAGLINE = "SIREN MEMORY POST"

PRESETS = {
    "快速": dict(max_side=768, steps=400, hidden=96, layers=3, residual_scale=2, residual_quality=90),
    "平衡": dict(max_side=1024, steps=800, hidden=128, layers=4, residual_scale=1, residual_quality=95),
    "高画质": dict(max_side=1536, steps=1200, hidden=192, layers=4, residual_scale=1, residual_quality=98),
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

STYLE = r"""
QWidget {
    color: #182033;
    font-family: "Segoe UI Variable Display", "Segoe UI", "Microsoft YaHei UI";
    font-size: 13px;
}
QFrame#Card {
    background-color: rgba(255, 255, 255, 150);
    border: 1px solid rgba(255, 255, 255, 220);
    border-radius: 22px;
}
QFrame#SoftCard {
    background-color: rgba(255, 255, 255, 92);
    border: 1px solid rgba(255, 255, 255, 185);
    border-radius: 16px;
}
QLabel#HeroTitle {
    color: #111827;
    font-size: 27px;
    font-weight: 700;
}
QLabel#HeroSub {
    color: #6C7689;
    font-size: 13px;
}
QLabel#SectionTitle {
    color: #20283A;
    font-size: 15px;
    font-weight: 700;
}
QLabel#FieldLabel {
    color: #687386;
    font-size: 12px;
}
QLabel#Muted {
    color: #778196;
    font-size: 12px;
}
QLabel#Tiny {
    color: #8A93A5;
    font-size: 11px;
}
QLabel#CountPill {
    background-color: rgba(91, 124, 250, 26);
    color: #435ED6;
    border: 1px solid rgba(91, 124, 250, 41);
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#PrivacyPill {
    background-color: rgba(255, 255, 255, 132);
    color: #63708A;
    border: 1px solid rgba(255, 255, 255, 210);
    border-radius: 13px;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 600;
}
QFrame#Segment {
    background-color: rgba(255, 255, 255, 112);
    border: 1px solid rgba(255, 255, 255, 190);
    border-radius: 15px;
}
QPushButton#SegmentButton {
    background-color: transparent;
    color: #697488;
    border: none;
    border-radius: 12px;
    padding: 8px 22px;
    font-weight: 600;
}
QPushButton#SegmentButton:hover {
    color: #4054B5;
    background-color: rgba(255, 255, 255, 80);
}
QPushButton#SegmentButton:checked {
    background-color: rgba(255, 255, 255, 238);
    color: #3450C8;
}
QPushButton#WinButton {
    background-color: transparent;
    color: #677288;
    border: none;
    border-radius: 10px;
    font-size: 17px;
    font-weight: 500;
}
QPushButton#WinButton:hover {
    background-color: rgba(70, 84, 112, 18);
    color: #283247;
}
QPushButton#CloseWinButton {
    background-color: transparent;
    color: #677288;
    border: none;
    border-radius: 10px;
    font-size: 18px;
    font-weight: 500;
}
QPushButton#CloseWinButton:hover {
    background-color: #FF5F57;
    color: white;
}
QPushButton#PrimaryButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5B7CFA, stop:1 #8B5CF6);
    color: white;
    border: none;
    border-radius: 14px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: 700;
}
QPushButton#PrimaryButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6C89FF, stop:1 #9B6BFF);
}
QPushButton#PrimaryButton:pressed {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4D6EEB, stop:1 #7C4FE0);
}
QPushButton#PrimaryButton:disabled {
    background-color: rgba(155, 166, 190, 95);
    color: rgba(255, 255, 255, 220);
}
QPushButton#SecondaryButton {
    background-color: rgba(255, 255, 255, 166);
    color: #3E4A61;
    border: 1px solid rgba(105, 120, 150, 48);
    border-radius: 12px;
    padding: 9px 16px;
    font-weight: 600;
}
QPushButton#SecondaryButton:hover {
    background-color: rgba(255, 255, 255, 235);
    border: 1px solid rgba(91, 124, 250, 90);
    color: #3448A4;
}
QPushButton#GhostButton {
    background-color: transparent;
    color: #64718A;
    border: none;
    padding: 6px 9px;
    font-weight: 600;
}
QPushButton#GhostButton:hover {
    color: #3450C8;
    background-color: rgba(91, 124, 250, 17);
    border-radius: 9px;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: rgba(255, 255, 255, 174);
    color: #273044;
    border: 1px solid rgba(105, 120, 150, 42);
    border-radius: 10px;
    padding: 7px 10px;
    selection-background-color: #6B7DFF;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {
    border: 1px solid rgba(91, 124, 250, 86);
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    background-color: rgba(255, 255, 255, 232);
    border: 1px solid #6B7DFF;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #273044;
    border: 1px solid rgba(105, 120, 150, 45);
    border-radius: 10px;
    selection-background-color: #EEF2FF;
    selection-color: #253467;
    outline: none;
    padding: 5px;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 17px;
    border: none;
    background-color: transparent;
}
QCheckBox {
    color: #566176;
    spacing: 9px;
    font-size: 12px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid rgba(85, 100, 135, 80);
    background-color: rgba(255, 255, 255, 220);
}
QCheckBox::indicator:hover {
    border: 1px solid #5B7CFA;
}
QCheckBox::indicator:checked {
    background-color: #5B7CFA;
    border: 1px solid #5B7CFA;
}
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
    padding: 0px;
}
QListWidget::item {
    background-color: rgba(255, 255, 255, 108);
    color: #303A4E;
    border: 1px solid rgba(255, 255, 255, 176);
    border-radius: 12px;
    padding: 5px;
    margin: 3px 0px;
}
QListWidget::item:hover {
    background-color: rgba(255, 255, 255, 170);
}
QListWidget::item:selected {
    background-color: rgba(91, 124, 250, 30);
    color: #1F2E63;
    border: 1px solid rgba(91, 124, 250, 120);
}
QFrame#DropZone {
    background-color: rgba(255, 255, 255, 82);
    border: 2px dashed rgba(118, 136, 172, 82);
    border-radius: 18px;
}
QFrame#DropZone:hover {
    background-color: rgba(255, 255, 255, 128);
    border: 2px dashed rgba(91, 124, 250, 128);
}
QFrame#DropZone[dragActive="true"] {
    background-color: rgba(91, 124, 250, 25);
    border: 2px solid #5B7CFA;
}
QProgressBar {
    background-color: rgba(120, 135, 170, 35);
    border: none;
    border-radius: 4px;
    min-height: 8px;
    max-height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    border-radius: 4px;
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5B7CFA, stop:0.55 #7C72FF, stop:1 #B45CFF);
}
QTextEdit#LogView {
    background-color: rgba(248, 250, 253, 188);
    color: #58647A;
    border: 1px solid rgba(105, 120, 150, 28);
    border-radius: 14px;
    padding: 8px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 11px;
    selection-background-color: #DCE4FF;
}
QLabel#StatusText {
    color: #5F6B80;
    font-size: 12px;
    font-weight: 600;
}
QLabel#Toast {
    background-color: rgba(31, 41, 59, 238);
    color: white;
    border-radius: 14px;
    padding: 12px 20px;
    font-weight: 600;
}
QLabel#ToastError {
    background-color: rgba(191, 52, 66, 242);
    color: white;
    border-radius: 14px;
    padding: 12px 20px;
    font-weight: 600;
}
QToolTip {
    background-color: #202838;
    color: white;
    border: none;
    padding: 6px;
}
"""


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def human_size(size: int | float) -> str:
    size = float(size)
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.2f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{int(size)} B"


def current_app_exe() -> Path | None:
    if getattr(sys, "frozen", False):
        path = Path(sys.executable)
        return path if path.exists() else None
    base = Path(__file__).resolve().parent
    for name in ("记忆邮局.exe", "MemoryPost.exe", "dist/MemoryPost.exe", "dist/SIRENSender.exe"):
        path = base / name
        if path.exists():
            return path
    return None


def add_shadow(widget: QWidget, blur: int = 34, y: int = 9, alpha: int = 24):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(61, 80, 125, alpha))
    widget.setGraphicsEffect(effect)
    return effect


def divider() -> QFrame:
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet("background: rgba(92, 107, 140, 22); border: none;")
    return line


def make_label(text: str, name: str = "") -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    return label


def rounded_thumb(path: str, size: int = 48) -> QPixmap:
    source = QPixmap(path)
    if source.isNull():
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        return pix
    scaled = source.scaled(
        size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - size) // 2)
    y = max(0, (scaled.height() - size) // 2)
    cropped = scaled.copy(x, y, size, size)
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, size, size), 11, 11)
    painter.setClipPath(clip)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return result


class LogoMark(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(42, 42)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1, 1, 40, 40)
        path = QPainterPath()
        path.addRoundedRect(rect, 13, 13)
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, QColor("#5B7CFA"))
        grad.setColorAt(1, QColor("#A855F7"))
        p.fillPath(path, grad)
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        p.drawPath(path)
        p.setPen(QPen(QColor(255, 255, 255, 235), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        wave = QPainterPath()
        for i in range(31):
            x = 9 + i * 0.78
            y = 21 + math.sin(i / 30 * math.pi * 2.1) * 6.2
            if i == 0:
                wave.moveTo(x, y)
            else:
                wave.lineTo(x, y)
        p.drawPath(wave)
        p.setBrush(QColor(255, 255, 255, 235))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(31.3, 13.0), 1.8, 1.8)
        p.end()


class DropZone(QFrame):
    clicked = pyqtSignal()
    filesDropped = pyqtSignal(list)

    def __init__(self, title: str, subtitle: str, suffixes: set[str], compact: bool = False, parent=None):
        super().__init__(parent)
        self.suffixes = suffixes
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(112 if compact else 148)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("＋")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("color: #7D8DAD; font-size: 28px; font-weight: 300;")
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #38445B; font-size: 13px; font-weight: 650;")
        self.sub_label = QLabel(subtitle)
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("color: #8992A4; font-size: 11px;")
        layout.addWidget(icon)
        layout.addWidget(self.title_label)
        layout.addWidget(self.sub_label)

    def _repolish(self):
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _paths(self, event) -> list[str]:
        paths = []
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in self.suffixes:
                paths.append(str(path))
        return paths

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and self._paths(event):
            event.acceptProposedAction()
            self.setProperty("dragActive", True)
            self._repolish()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragActive", False)
        self._repolish()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        paths = self._paths(event)
        self.setProperty("dragActive", False)
        self._repolish()
        if paths:
            self.filesDropped.emit(paths)
            event.acceptProposedAction()


class TitleBar(QFrame):
    tabChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_offset: QPoint | None = None
        self.setFixedHeight(66)
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(12)

        logo = LogoMark()
        brand = QVBoxLayout()
        brand.setSpacing(0)
        name = QLabel(APP_NAME)
        name.setStyleSheet("color: #172033; font-size: 16px; font-weight: 750;")
        tag = QLabel(APP_TAGLINE)
        tag.setStyleSheet("color: #929BAD; font-size: 9px; font-weight: 650; letter-spacing: 1px;")
        brand.addWidget(name)
        brand.addWidget(tag)
        layout.addWidget(logo)
        layout.addLayout(brand)
        layout.addStretch(1)

        segment = QFrame()
        segment.setObjectName("Segment")
        seg_layout = QHBoxLayout(segment)
        seg_layout.setContentsMargins(4, 4, 4, 4)
        seg_layout.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.send_button = QPushButton("发送")
        self.receive_button = QPushButton("接收")
        for i, button in enumerate((self.send_button, self.receive_button)):
            button.setObjectName("SegmentButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(button, i)
            seg_layout.addWidget(button)
        self.send_button.setChecked(True)
        self.group.idClicked.connect(self.tabChanged.emit)
        layout.addWidget(segment)
        layout.addStretch(1)

        self.min_button = QPushButton("—")
        self.min_button.setObjectName("WinButton")
        self.min_button.setFixedSize(38, 34)
        self.min_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("CloseWinButton")
        self.close_button.setFixedSize(38, 34)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.min_button)
        layout.addWidget(self.close_button)

    def set_tab(self, index: int):
        self.send_button.setChecked(index == 0)
        self.receive_button.setChecked(index == 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.window().isMaximized():
                self.window().showNormal()
            else:
                self.window().showMaximized()
        super().mouseDoubleClickEvent(event)


class Toast(QLabel):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setObjectName("Toast")
        self.hide()

    def show_message(self, text: str, error: bool = False, duration: int = 3200):
        self.setObjectName("ToastError" if error else "Toast")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        x = max(20, (parent.width() - self.width()) // 2)
        y = max(20, parent.height() - self.height() - 42)
        self.move(x, y)
        self.show()
        self.raise_()
        QTimer.singleShot(duration, self.hide)


class SendWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(float, str)
    completed = pyqtSignal(object)
    cancelled = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, images, args, output: Path, cancel_event: threading.Event, parent=None):
        super().__init__(parent)
        self.images = list(images)
        self.args = args
        self.output = output
        self.cancel_event = cancel_event

    def run(self):
        last = [0.0]

        def on_progress(fraction, text):
            now = time.time()
            if now - last[0] >= 0.08 or fraction >= 1.0:
                last[0] = now
                self.progress.emit(float(fraction), str(text))

        try:
            summary = build_bundle(
                self.images,
                self.args,
                self.output,
                log=self.log.emit,
                progress=on_progress,
                cancel_event=self.cancel_event,
            )
            self.completed.emit(summary)
        except RuntimeError as exc:
            if str(exc) == "cancelled":
                self.cancelled.emit()
            else:
                self.failed.emit(traceback.format_exc())
        except Exception:
            self.failed.emit(traceback.format_exc())


class ReceiveWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(float, str)
    completed = pyqtSignal(object)
    cancelled = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, bundle: str, output: str, fmt: str, quality: int, cancel_event: threading.Event, parent=None):
        super().__init__(parent)
        self.bundle = bundle
        self.output = output
        self.fmt = fmt
        self.quality = quality
        self.cancel_event = cancel_event

    def run(self):
        last = [0.0]

        def on_progress(fraction, text):
            now = time.time()
            if now - last[0] >= 0.08 or fraction >= 1.0:
                last[0] = now
                self.progress.emit(float(fraction), str(text))

        try:
            outputs = reconstruct_bundle(
                self.bundle,
                self.output,
                log=self.log.emit,
                progress=on_progress,
                fmt=self.fmt,
                quality=self.quality,
                cancel_event=self.cancel_event,
            )
            self.completed.emit(outputs)
        except RuntimeError as exc:
            if str(exc) == "cancelled":
                self.cancelled.emit()
            else:
                self.failed.emit(traceback.format_exc())
        except Exception:
            self.failed.emit(traceback.format_exc())


class SenderPage(QWidget):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.images: list[str] = []
        self.worker: SendWorker | None = None
        self.cancel_event = threading.Event()
        self.running = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        hero = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(make_label("把照片，寄进一张模型里。", "HeroTitle"))
        titles.addWidget(make_label("训练专属记忆网络，连同极轻的残差一起打包发送。", "HeroSub"))
        hero.addLayout(titles)
        hero.addStretch(1)
        privacy = make_label("本地处理  ·  不上传", "PrivacyPill")
        hero.addWidget(privacy, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(hero)

        main_row = QHBoxLayout()
        main_row.setSpacing(14)

        left_card = QFrame()
        left_card.setObjectName("Card")
        add_shadow(left_card, 30, 8, 20)
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(20, 17, 20, 17)
        left_layout.setSpacing(10)
        head = QHBoxLayout()
        head.addWidget(make_label("照片", "SectionTitle"))
        head.addStretch(1)
        self.count_label = make_label("0 张", "CountPill")
        head.addWidget(self.count_label)
        left_layout.addLayout(head)

        self.image_drop = DropZone(
            "拖入照片，或点击选择",
            "支持 JPG、PNG、WebP、BMP、TIFF",
            IMAGE_SUFFIXES,
            compact=False,
        )
        self.image_drop.clicked.connect(self.add_images)
        self.image_drop.filesDropped.connect(self._append_paths)
        left_layout.addWidget(self.image_drop)

        self.image_list = QListWidget()
        self.image_list.setIconSize(QSize(46, 46))
        self.image_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.image_list.setMinimumHeight(118)
        self.image_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        left_layout.addWidget(self.image_list, 1)

        list_actions = QHBoxLayout()
        list_actions.setSpacing(6)
        add_btn = QPushButton("添加照片")
        add_btn.setObjectName("SecondaryButton")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_images)
        remove_btn = QPushButton("移除选中")
        remove_btn.setObjectName("GhostButton")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(self.remove_selected)
        clear_btn = QPushButton("清空")
        clear_btn.setObjectName("GhostButton")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_images)
        list_actions.addWidget(add_btn)
        list_actions.addWidget(remove_btn)
        list_actions.addWidget(clear_btn)
        list_actions.addStretch(1)
        left_layout.addLayout(list_actions)
        main_row.addWidget(left_card, 3)

        right_card = QFrame()
        right_card.setObjectName("Card")
        add_shadow(right_card, 30, 8, 18)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(20, 17, 20, 17)
        right_layout.setSpacing(8)
        right_layout.addWidget(make_label("记忆参数", "SectionTitle"))

        preset_row = QHBoxLayout()
        preset_row.setSpacing(10)
        preset_row.addWidget(make_label("预设", "FieldLabel"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["快速", "平衡", "高画质", "自定义"])
        self.preset_combo.setCurrentText("平衡")
        self.preset_combo.currentTextChanged.connect(self._apply_preset)
        preset_row.addWidget(self.preset_combo, 1)
        right_layout.addLayout(preset_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(7)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem("自动 · 按原图", "auto")
        self.resolution_combo.addItem("固定长边", "fixed")
        self.resolution_combo.setToolTip("自动：小图不放大；大图长边不超过设定值，总量不超过约 160 万像素")
        self.max_side_spin = self._int_spin(64, 2048, 1024, 64)
        self.group_spin = self._int_spin(1, 8, 1, 1)
        self.group_spin.setToolTip("1 = 每张照片独立模型；2-8 = 按列表顺序每 N 张共用一个共享模型")
        self.steps_spin = self._int_spin(10, 20000, 800, 50)
        self.hidden_spin = self._int_spin(16, 512, 128, 16)
        self.layers_spin = self._int_spin(1, 8, 4, 1)
        self.quality_spin = self._int_spin(1, 100, 95, 1)
        self.scale_combo = QComboBox()
        for text, value in (("全分辨率", 1), ("1 / 2", 2), ("1 / 4", 4)):
            self.scale_combo.addItem(text, value)
        self.format_combo = QComboBox()
        self.format_combo.addItem("WebP · 更小", "webp")
        self.format_combo.addItem("PNG · 无损", "png")

        self._add_field(grid, 0, 0, "分辨率", self.resolution_combo)
        self._add_field(grid, 0, 2, "最长边 / 上限", self.max_side_spin)
        self._add_field(grid, 1, 0, "每模型照片数", self.group_spin)
        self._add_field(grid, 1, 2, "训练步数", self.steps_spin)
        self._add_field(grid, 2, 0, "隐藏宽度", self.hidden_spin)
        self._add_field(grid, 2, 2, "隐藏层数", self.layers_spin)
        self._add_field(grid, 3, 0, "残差尺度", self.scale_combo)
        self._add_field(grid, 3, 2, "残差质量", self.quality_spin)
        self._add_field(grid, 4, 0, "残差格式", self.format_combo)
        self.advanced_value = make_label("自动 ≤1024 px · 1 张/模型", "Tiny")
        self._add_field(grid, 4, 2, "当前组合", self.advanced_value)
        right_layout.addLayout(grid)

        self.resolution_combo.currentIndexChanged.connect(self._settings_changed)
        self.max_side_spin.valueChanged.connect(self._settings_changed)
        self.group_spin.valueChanged.connect(self._settings_changed)
        self.steps_spin.valueChanged.connect(self._settings_changed)
        self.hidden_spin.valueChanged.connect(self._settings_changed)
        self.layers_spin.valueChanged.connect(self._settings_changed)

        out_label = make_label("输出包裹", "FieldLabel")
        right_layout.addWidget(out_label)
        out_row = QHBoxLayout()
        out_row.setSpacing(7)
        self.output_edit = QLineEdit(str(Path.cwd() / "记忆包裹.zip"))
        self.output_edit.setClearButtonEnabled(True)
        out_row.addWidget(self.output_edit, 1)
        browse_btn = QPushButton("选择…")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_output)
        out_row.addWidget(browse_btn)
        right_layout.addLayout(out_row)

        self.fast_large_check = QCheckBox("大图加速：基础图低分辨率渲染，残差补细节")
        self.fast_large_check.setChecked(True)
        self.fast_large_check.setToolTip("对超过约 90 万像素的基础图先低分辨率渲染，再叠加高分辨率残差")
        right_layout.addWidget(self.fast_large_check)

        self_exe = current_app_exe()
        extra_text = f"，约 +{human_size(self_exe.stat().st_size)}" if self_exe else ""
        self.include_exe_check = QCheckBox(f"把本工具一起放进包裹（朋友无需另收 exe{extra_text}）")
        self.include_exe_check.setChecked(False)
        right_layout.addWidget(self.include_exe_check)
        right_layout.addStretch(1)
        main_row.addWidget(right_card, 2)
        root.addLayout(main_row, 1)

        action_card = QFrame()
        action_card.setObjectName("Card")
        add_shadow(action_card, 28, 7, 16)
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(20, 13, 20, 13)
        action_layout.setSpacing(8)
        status_row = QHBoxLayout()
        self.status_label = make_label("就绪 · 选择照片后开始", "StatusText")
        self.percent_label = make_label("0%", "Tiny")
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        status_row.addWidget(self.percent_label)
        action_layout.addLayout(status_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        action_layout.addWidget(self.progress)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.start_btn = QPushButton("生成记忆包裹")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_training)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_training)
        self.open_btn = QPushButton("打开所在文件夹")
        self.open_btn.setObjectName("GhostButton")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.clicked.connect(self.open_output_folder)
        self.log_btn = QPushButton("运行详情")
        self.log_btn.setObjectName("GhostButton")
        self.log_btn.setCheckable(True)
        self.log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_btn.toggled.connect(self._toggle_log)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.cancel_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.open_btn)
        buttons.addWidget(self.log_btn)
        action_layout.addLayout(buttons)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(92)
        self.log_view.setMaximumHeight(120)
        self.log_view.hide()
        action_layout.addWidget(self.log_view)
        root.addWidget(action_card)

        self._apply_preset("平衡")

    def _int_spin(self, low, high, value, step):
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setSingleStep(step)
        spin.setValue(value)
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        return spin

    def _add_field(self, grid, row, col, text, widget):
        grid.addWidget(make_label(text, "FieldLabel"), row, col)
        grid.addWidget(widget, row, col + 1)

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择照片",
            str(Path.home()),
            "图片 (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;所有文件 (*.*)",
        )
        if files:
            self._append_paths(files)

    def _append_paths(self, paths):
        for raw in paths:
            path = str(Path(raw).resolve())
            if Path(path).suffix.lower() not in IMAGE_SUFFIXES or path in self.images:
                continue
            self.images.append(path)
            item = QListWidgetItem(QIcon(rounded_thumb(path, 46)), "")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setSizeHint(QSize(0, 62))
            self.image_list.addItem(item)
        if self.images:
            first = Path(self.images[0])
            if self.output_edit.text().strip() in ("", str(Path.cwd() / "记忆包裹.zip")):
                self.output_edit.setText(str(first.with_name("记忆包裹.zip")))
            self.image_drop.title_label.setText(f"已选择 {len(self.images)} 张照片")
            self.image_drop.sub_label.setText("可以继续拖入，或点击再次添加")
        self._refresh_count()
        self._refresh_list_labels()

    def _image_size(self, path: str) -> tuple[int, int]:
        reader = QImageReader(path)
        size = reader.size()
        if size.isValid():
            return int(size.width()), int(size.height())
        pixmap = QPixmap(path)
        return int(pixmap.width()), int(pixmap.height())

    def _refresh_list_labels(self):
        if not hasattr(self, "resolution_combo"):
            return
        mode = str(self.resolution_combo.currentData() or "auto")
        max_side = int(self.max_side_spin.value())
        group_size = max(1, int(self.group_spin.value()))
        for index in range(self.image_list.count()):
            item = self.image_list.item(index)
            path = item.data(Qt.ItemDataRole.UserRole)
            if not path:
                continue
            source_w, source_h = self._image_size(path)
            target_w, target_h, _ = compute_target_size(source_w, source_h, mode, max_side)
            group_text = "独立模型" if group_size == 1 else f"模型组 {index // group_size + 1}"
            size_text = human_size(Path(path).stat().st_size)
            item.setText(
                f"{Path(path).name}\n"
                f"{source_w}×{source_h} → {target_w}×{target_h} · {group_text} · {size_text}"
            )
            item.setToolTip(f"{path}\n训练分辨率：{target_w}×{target_h}")

    def _sync_advanced_text(self):
        if not hasattr(self, "advanced_value"):
            return
        mode = "自动" if str(self.resolution_combo.currentData()) == "auto" else "固定"
        group = int(self.group_spin.value())
        group_text = "独立" if group == 1 else f"{group} 张/模型"
        self.advanced_value.setText(
            f"{mode} ≤{self.max_side_spin.value()}px · {group_text} · {self.steps_spin.value()}步"
        )

    def _settings_changed(self, *args):
        self._refresh_list_labels()
        self._sync_advanced_text()

    def _refresh_count(self):
        self.count_label.setText(f"{len(self.images)} 张")
        if not self.images:
            self.image_drop.title_label.setText("拖入照片，或点击选择")
            self.image_drop.sub_label.setText("支持 JPG、PNG、WebP、BMP、TIFF")

    def remove_selected(self):
        rows = sorted({self.image_list.row(item) for item in self.image_list.selectedItems()}, reverse=True)
        for row in rows:
            item = self.image_list.takeItem(row)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in self.images:
                self.images.remove(path)
        self._refresh_count()

    def clear_images(self):
        self.images.clear()
        self.image_list.clear()
        self._refresh_count()

    def _apply_preset(self, name: str):
        if name not in PRESETS:
            return
        preset = PRESETS[name]
        controls = (
            self.resolution_combo, self.max_side_spin, self.steps_spin,
            self.hidden_spin, self.layers_spin, self.quality_spin,
        )
        for control in controls:
            control.blockSignals(True)
        try:
            auto_index = self.resolution_combo.findData("auto")
            if auto_index >= 0:
                self.resolution_combo.setCurrentIndex(auto_index)
            self.max_side_spin.setValue(preset["max_side"])
            self.steps_spin.setValue(preset["steps"])
            self.hidden_spin.setValue(preset["hidden"])
            self.layers_spin.setValue(preset["layers"])
            self.quality_spin.setValue(preset["residual_quality"])
            index = self.scale_combo.findData(preset["residual_scale"])
            if index >= 0:
                self.scale_combo.setCurrentIndex(index)
        finally:
            for control in controls:
                control.blockSignals(False)
        self._settings_changed()

    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存记忆包裹",
            self.output_edit.text().strip() or str(Path.home() / "记忆包裹.zip"),
            "ZIP 包裹 (*.zip)",
        )
        if path:
            if not path.lower().endswith(".zip"):
                path += ".zip"
            self.output_edit.setText(path)

    def _parse_args(self):
        if not self.images:
            raise ValueError("请先添加至少一张照片。")
        output_text = self.output_edit.text().strip()
        if not output_text:
            raise ValueError("请选择输出包裹路径。")
        output = Path(output_text)
        if output.suffix.lower() != ".zip":
            output = output.with_suffix(".zip")
        return SimpleNamespace(
            size=self.max_side_spin.value(),
            max_side=self.max_side_spin.value(),
            max_pixels=1_600_000,
            resolution_mode=str(self.resolution_combo.currentData()),
            model_group_size=int(self.group_spin.value()),
            steps=self.steps_spin.value(),
            batch=8192,
            hidden=self.hidden_spin.value(),
            layers=self.layers_spin.value(),
            freqs="1,2,4,8",
            omega0=30.0,
            lr=1e-3,
            residual_scale=int(self.scale_combo.currentData()),
            residual_quality=self.quality_spin.value(),
            residual_format=str(self.format_combo.currentData()),
            large_image_fast=bool(self.fast_large_check.isChecked()),
            base_render_pixels=900_000,
            seed=1234,
            include_receiver_exe=bool(self.include_exe_check.isChecked()),
        ), output

    def _set_busy(self, busy: bool):
        self.running = busy
        self.start_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.image_drop.setEnabled(not busy)
        for widget in (self.preset_combo, self.resolution_combo, self.max_side_spin,
                       self.group_spin, self.steps_spin, self.hidden_spin,
                       self.layers_spin, self.scale_combo, self.quality_spin,
                       self.format_combo, self.output_edit, self.fast_large_check,
                       self.include_exe_check):
            widget.setEnabled(not busy)

    def start_training(self):
        if self.running:
            return
        try:
            args, output = self._parse_args()
        except ValueError as exc:
            QMessageBox.warning(self, "参数不完整", str(exc))
            return
        self.cancel_event.clear()
        self._set_busy(True)
        self.progress.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("准备训练…")
        self.log_view.clear()
        self._append_log("=" * 66)
        self._append_log(f"照片：{len(self.images)} 张")
        self._append_log(f"输出：{output}")
        mode_text = "自动按原图" if args.resolution_mode == "auto" else "固定长边"
        self._append_log(
            f"参数：{mode_text} ≤{args.max_side}px / 每模型 {args.model_group_size} 张 / "
            f"{args.steps} 步 / {args.hidden}×{args.layers} / "
            f"残差 {args.residual_scale} q{args.residual_quality}"
        )
        self.worker = SendWorker(self.images, args, output, self.cancel_event, self)
        self.worker.log.connect(self._append_log)
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
        self.worker.cancelled.connect(self._on_cancelled)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(lambda: self.worker.deleteLater() if self.worker else None)
        self.worker.start()

    def cancel_training(self):
        if self.running:
            self.cancel_event.set()
            self.status_label.setText("正在取消…")
            self.cancel_btn.setEnabled(False)

    def _on_progress(self, fraction: float, text: str):
        value = max(0, min(1000, int(fraction * 1000)))
        self.progress.setValue(value)
        self.percent_label.setText(f"{value / 10:.0f}%")
        self.status_label.setText(text)

    def _on_completed(self, summary):
        self._set_busy(False)
        self.progress.setValue(1000)
        self.percent_label.setText("100%")
        size = human_size(summary["bundle_bytes"])
        self.status_label.setText(f"完成 · {size}")
        self._append_log(f"完成：{summary['bundle']}")
        self._append_log(f"包裹大小：{size} · 总耗时 {summary['total_seconds']:.1f}s")
        self.window.toast(f"记忆包裹已生成 · {size}")

    def _on_cancelled(self):
        self._set_busy(False)
        self.status_label.setText("已取消")
        self._append_log("已取消。")
        self.window.toast("已取消本次训练")

    def _on_failed(self, tb: str):
        self._set_busy(False)
        self.status_label.setText("训练失败")
        self._append_log(tb)
        self.log_btn.setChecked(True)
        self.window.toast("训练失败，详情已写入运行日志", error=True)

    def _append_log(self, text: str):
        self.log_view.append(text)
        bar = self.log_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _toggle_log(self, visible: bool):
        self.log_view.setVisible(visible)
        self.log_view.setMaximumHeight(120 if visible else 0)
        self.log_btn.setText("收起详情" if visible else "运行详情")

    def open_output_folder(self):
        path = Path(self.output_edit.text().strip() or ".")
        folder = path.parent if path.parent.exists() else Path.cwd()
        try:
            os.startfile(str(folder))
        except Exception as exc:
            self.window.toast(f"无法打开文件夹：{exc}", error=True)


class ReceiverPage(QWidget):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.bundle_path: str | None = None
        self.worker: ReceiveWorker | None = None
        self.cancel_event = threading.Event()
        self.running = False
        self._auto_start_pending = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        hero = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(make_label("打开一份会发光的记忆。", "HeroTitle"))
        titles.addWidget(make_label("选择朋友寄来的记忆包裹，在本地还原完整照片。", "HeroSub"))
        hero.addLayout(titles)
        hero.addStretch(1)
        hero.addWidget(make_label("离线重建  ·  无需 Python", "PrivacyPill"), 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(hero)

        main_row = QHBoxLayout()
        main_row.setSpacing(14)

        bundle_card = QFrame()
        bundle_card.setObjectName("Card")
        add_shadow(bundle_card, 30, 8, 20)
        bundle_layout = QVBoxLayout(bundle_card)
        bundle_layout.setContentsMargins(20, 17, 20, 17)
        bundle_layout.setSpacing(10)
        bundle_layout.addWidget(make_label("记忆包裹", "SectionTitle"))

        self.bundle_drop = DropZone(
            "拖入 记忆包裹.zip",
            "或点击选择朋友发来的 ZIP 文件",
            {".zip"},
            compact=False,
        )
        self.bundle_drop.clicked.connect(self.choose_bundle)
        self.bundle_drop.filesDropped.connect(lambda paths: self.set_bundle(paths[0]) if paths else None)
        bundle_layout.addWidget(self.bundle_drop)

        info_card = QFrame()
        info_card.setObjectName("SoftCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(15, 12, 15, 12)
        info_layout.setSpacing(3)
        self.bundle_name = make_label("尚未选择包裹", "SectionTitle")
        self.bundle_name.setStyleSheet("font-size: 13px;")
        self.bundle_meta = make_label("包裹中包含模型、残差和图片清单。", "Muted")
        info_layout.addWidget(self.bundle_name)
        info_layout.addWidget(self.bundle_meta)
        bundle_layout.addWidget(info_card)
        bundle_layout.addStretch(1)

        choose_row = QHBoxLayout()
        choose_btn = QPushButton("选择记忆包裹")
        choose_btn.setObjectName("SecondaryButton")
        choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_btn.clicked.connect(self.choose_bundle)
        choose_row.addWidget(choose_btn)
        choose_row.addStretch(1)
        bundle_layout.addLayout(choose_row)
        main_row.addWidget(bundle_card, 3)

        output_card = QFrame()
        output_card.setObjectName("Card")
        add_shadow(output_card, 30, 8, 18)
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(20, 17, 20, 17)
        output_layout.setSpacing(10)
        output_layout.addWidget(make_label("输出设置", "SectionTitle"))

        output_layout.addWidget(make_label("保存到", "FieldLabel"))
        out_row = QHBoxLayout()
        out_row.setSpacing(7)
        self.output_edit = QLineEdit(str(Path.cwd() / "received"))
        self.output_edit.setClearButtonEnabled(True)
        out_row.addWidget(self.output_edit, 1)
        out_browse = QPushButton("选择…")
        out_browse.setObjectName("SecondaryButton")
        out_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        out_browse.clicked.connect(self.browse_output)
        out_row.addWidget(out_browse)
        output_layout.addLayout(out_row)

        output_layout.addWidget(make_label("图片格式", "FieldLabel"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("PNG · 无损", "png")
        self.format_combo.addItem("JPG · 更小", "jpg")
        self.format_combo.currentIndexChanged.connect(self._sync_quality)
        output_layout.addWidget(self.format_combo)

        output_layout.addWidget(make_label("JPG 质量", "FieldLabel"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.setEnabled(False)
        output_layout.addWidget(self.quality_spin)

        tip = QFrame()
        tip.setObjectName("SoftCard")
        tip_layout = QVBoxLayout(tip)
        tip_layout.setContentsMargins(14, 11, 14, 11)
        tip_layout.setSpacing(3)
        tip_label = make_label("重建说明", "FieldLabel")
        tip_text = make_label("模型先生成基础画面，再叠加极轻残差，得到接近原图的结果。", "Tiny")
        tip_text.setWordWrap(True)
        tip_layout.addWidget(tip_label)
        tip_layout.addWidget(tip_text)
        output_layout.addWidget(tip)
        output_layout.addStretch(1)
        main_row.addWidget(output_card, 2)
        root.addLayout(main_row, 1)

        action_card = QFrame()
        action_card.setObjectName("Card")
        add_shadow(action_card, 28, 7, 16)
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(20, 13, 20, 13)
        action_layout.setSpacing(8)
        status_row = QHBoxLayout()
        self.status_label = make_label("就绪 · 选择记忆包裹", "StatusText")
        self.percent_label = make_label("0%", "Tiny")
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        status_row.addWidget(self.percent_label)
        action_layout.addLayout(status_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        action_layout.addWidget(self.progress)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.start_btn = QPushButton("还原完整照片")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_reconstruct)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_reconstruct)
        self.open_btn = QPushButton("打开输出文件夹")
        self.open_btn.setObjectName("GhostButton")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.clicked.connect(self.open_output_folder)
        self.log_btn = QPushButton("运行详情")
        self.log_btn.setObjectName("GhostButton")
        self.log_btn.setCheckable(True)
        self.log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_btn.toggled.connect(self._toggle_log)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.cancel_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.open_btn)
        buttons.addWidget(self.log_btn)
        action_layout.addLayout(buttons)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(92)
        self.log_view.setMaximumHeight(120)
        self.log_view.hide()
        action_layout.addWidget(self.log_view)
        root.addWidget(action_card)

    def choose_bundle(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择记忆包裹",
            str(Path.home()),
            "记忆包裹 (*.zip);;所有文件 (*.*)",
        )
        if path:
            self.set_bundle(path)

    def set_bundle(self, path: str, auto_start: bool = False):
        path_obj = Path(path).resolve()
        if not path_obj.exists() or path_obj.suffix.lower() != ".zip":
            self.window.toast("请选择有效的 ZIP 记忆包裹", error=True)
            return
        self.bundle_path = str(path_obj)
        self.bundle_drop.title_label.setText("记忆包裹已就位")
        self.bundle_drop.sub_label.setText("点击可更换包裹")
        self.bundle_name.setText(path_obj.name)
        self.bundle_meta.setText(f"{human_size(path_obj.stat().st_size)} · {path_obj.parent}")
        self.output_edit.setText(str(path_obj.parent / "received"))
        self._auto_start_pending = bool(auto_start)
        if auto_start:
            QTimer.singleShot(450, self.start_reconstruct)

    def browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出文件夹", self.output_edit.text().strip() or str(Path.home()))
        if path:
            self.output_edit.setText(path)

    def _sync_quality(self):
        self.quality_spin.setEnabled(self.format_combo.currentData() == "jpg")

    def _set_busy(self, busy: bool):
        self.running = busy
        self.start_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.bundle_drop.setEnabled(not busy)
        for widget in (self.output_edit, self.format_combo, self.quality_spin):
            widget.setEnabled(not busy)
        if not busy:
            self._sync_quality()

    def start_reconstruct(self):
        if self.running:
            return
        if not self.bundle_path:
            QMessageBox.warning(self, "缺少记忆包裹", "请先选择 bundle.zip。")
            return
        output = self.output_edit.text().strip() or str(Path(self.bundle_path).parent / "received")
        self.cancel_event.clear()
        self._set_busy(True)
        self.progress.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("准备重建…")
        self.log_view.clear()
        self._append_log("=" * 66)
        self._append_log(f"包裹：{self.bundle_path}")
        self._append_log(f"输出：{output}")
        self.worker = ReceiveWorker(
            self.bundle_path,
            output,
            str(self.format_combo.currentData()),
            self.quality_spin.value(),
            self.cancel_event,
            self,
        )
        self.worker.log.connect(self._append_log)
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
        self.worker.cancelled.connect(self._on_cancelled)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(lambda: self.worker.deleteLater() if self.worker else None)
        self.worker.start()

    def cancel_reconstruct(self):
        if self.running:
            self.cancel_event.set()
            self.status_label.setText("正在取消…")
            self.cancel_btn.setEnabled(False)

    def _on_progress(self, fraction: float, text: str):
        value = max(0, min(1000, int(fraction * 1000)))
        self.progress.setValue(value)
        self.percent_label.setText(f"{value / 10:.0f}%")
        self.status_label.setText(text)

    def _on_completed(self, outputs):
        self._set_busy(False)
        self.progress.setValue(1000)
        self.percent_label.setText("100%")
        self.status_label.setText(f"完成 · 已还原 {len(outputs)} 张照片")
        for path in outputs:
            self._append_log(f"输出：{path}")
        self.window.toast(f"已还原 {len(outputs)} 张照片")

    def _on_cancelled(self):
        self._set_busy(False)
        self.status_label.setText("已取消")
        self._append_log("已取消。")
        self.window.toast("已取消本次重建")

    def _on_failed(self, tb: str):
        self._set_busy(False)
        self.status_label.setText("重建失败")
        self._append_log(tb)
        self.log_btn.setChecked(True)
        self.window.toast("重建失败，详情已写入运行日志", error=True)

    def _append_log(self, text: str):
        self.log_view.append(text)
        bar = self.log_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _toggle_log(self, visible: bool):
        self.log_view.setVisible(visible)
        self.log_view.setMaximumHeight(120 if visible else 0)
        self.log_btn.setText("收起详情" if visible else "运行详情")

    def open_output_folder(self):
        folder = Path(self.output_edit.text().strip() or ".")
        if not folder.exists():
            folder = folder.parent if folder.parent.exists() else Path.cwd()
        try:
            os.startfile(str(folder))
        except Exception as exc:
            self.window.toast(f"无法打开文件夹：{exc}", error=True)


class GlassWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(940, 680)
        self.resize(1120, 820)
        icon_path = resource_path("assets/icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(8)

        self.titlebar = TitleBar()
        self.titlebar.min_button.clicked.connect(self.showMinimized)
        self.titlebar.close_button.clicked.connect(self.close)
        root.addWidget(self.titlebar)

        self.stack = QStackedWidget()
        self.sender_page = SenderPage(self)
        self.receiver_page = ReceiverPage(self)
        self.stack.addWidget(self.sender_page)
        self.stack.addWidget(self.receiver_page)
        root.addWidget(self.stack, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(6, 0, 2, 0)
        footer.addWidget(make_label("SIREN  ·  NumPy  ·  本地优先", "Tiny"))
        footer.addStretch(1)
        footer.addWidget(make_label(f"v{APP_VERSION}", "Tiny"))
        grip = QSizeGrip(self)
        grip.setFixedSize(18, 18)
        footer.addWidget(grip)
        root.addLayout(footer)

        self.titlebar.tabChanged.connect(self.switch_tab)
        self.toast_widget = Toast(self)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        outer = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        path = QPainterPath()
        path.addRoundedRect(outer, 32, 32)

        painter.setPen(Qt.PenStyle.NoPen)
        for offset, alpha in ((18, 7), (9, 12), (3, 18)):
            shadow_rect = outer.adjusted(offset, offset + 4, -offset, -offset + 4)
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(shadow_rect, 32, 32)
            painter.fillPath(shadow_path, QColor(52, 68, 105, alpha))

        painter.save()
        painter.setClipPath(path)
        base = QLinearGradient(outer.topLeft(), outer.bottomRight())
        base.setColorAt(0.0, QColor("#F9FBFF"))
        base.setColorAt(0.42, QColor("#EEF3FF"))
        base.setColorAt(0.75, QColor("#F7F2FF"))
        base.setColorAt(1.0, QColor("#FFF8FB"))
        painter.fillPath(path, base)

        blobs = (
            (QPointF(outer.left() + 150, outer.top() + 120), 330, QColor(91, 124, 250, 55)),
            (QPointF(outer.right() - 180, outer.top() + 150), 380, QColor(196, 110, 255, 42)),
            (QPointF(outer.left() + 310, outer.bottom() - 80), 310, QColor(88, 210, 255, 30)),
            (QPointF(outer.right() - 100, outer.bottom() - 20), 260, QColor(255, 144, 190, 28)),
        )
        for center, radius, color in blobs:
            radial = QRadialGradient(center, radius)
            radial.setColorAt(0.0, color)
            radial.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillRect(outer, radial)
        painter.restore()

        painter.setPen(QPen(QColor(255, 255, 255, 225), 1.3))
        painter.drawPath(path)
        painter.end()

    def switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.titlebar.set_tab(index)

    def toast(self, text: str, error: bool = False):
        self.toast_widget.show_message(text, error=error)

    def is_busy(self) -> bool:
        return self.sender_page.running or self.receiver_page.running

    def closeEvent(self, event):
        if self.is_busy():
            answer = QMessageBox.question(
                self,
                "任务仍在进行",
                "当前任务仍在运行，确定取消并退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.sender_page.cancel_event.set()
            self.receiver_page.cancel_event.set()
            for worker in (self.sender_page.worker, self.receiver_page.worker):
                if worker is not None and worker.isRunning():
                    worker.wait(900)
        event.accept()


def run_selftest(out_dir: Path, include_exe: bool = False) -> None:
    import numpy as np
    from PIL import Image

    import json
    import zipfile

    out_dir.mkdir(parents=True, exist_ok=True)
    height = width = 96
    yy, xx = np.mgrid[0:height, 0:width]
    arr1 = np.zeros((height, width, 3), dtype=np.uint8)
    arr1[..., 0] = (xx / max(1, width - 1) * 255).astype(np.uint8)
    arr1[..., 1] = (yy / max(1, height - 1) * 255).astype(np.uint8)
    arr1[..., 2] = (140 + 80 * np.sin(xx / 11.0)).clip(0, 255).astype(np.uint8)
    arr2 = np.zeros((height, width, 3), dtype=np.uint8)
    arr2[..., 0] = ((xx + yy) % 32 * 8).clip(0, 255).astype(np.uint8)
    arr2[..., 1] = (255 - yy / max(1, height - 1) * 220).astype(np.uint8)
    arr2[..., 2] = ((xx // 8 + yy // 8) % 2 * 180 + 40).astype(np.uint8)
    image_path_1 = out_dir / "selftest_a.png"
    image_path_2 = out_dir / "selftest_b.png"
    Image.fromarray(arr1, "RGB").save(image_path_1)
    Image.fromarray(arr2, "RGB").save(image_path_2)

    args = SimpleNamespace(
        size=96,
        max_side=96,
        max_pixels=1_600_000,
        resolution_mode="auto",
        model_group_size=2,
        steps=24,
        batch=2048,
        hidden=32,
        layers=2,
        freqs="1,2,4,8",
        omega0=30.0,
        lr=1e-3,
        residual_scale=1,
        residual_quality=92,
        residual_format="webp",
        large_image_fast=True,
        base_render_pixels=4_000,
        seed=1234,
        include_receiver_exe=bool(include_exe),
    )
    log_path = out_dir / "selftest.log"
    bundle_path = out_dir / "selftest_bundle.zip"
    with open(log_path, "w", encoding="utf-8") as log_file:
        summary = build_bundle(
            [str(image_path_1), str(image_path_2)],
            args,
            bundle_path,
            log=lambda line: (log_file.write(str(line) + "\n"), log_file.flush()),
        )
        outputs = reconstruct_bundle(
            str(bundle_path),
            out_dir / "received",
            log=lambda line: (log_file.write(str(line) + "\n"), log_file.flush()),
        )
        if len(outputs) != 2 or not all(Path(p).exists() for p in outputs):
            raise RuntimeError("selftest reconstruction did not produce both outputs")
        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))
        model_names = [name for name in names if name.startswith("models/") and name.endswith(".npz")]
        residual_names = [name for name in names if name.startswith("residuals/")]
        if len(model_names) != 1:
            raise RuntimeError(f"selftest expected one shared model, got {model_names}")
        if len(residual_names) != 2:
            raise RuntimeError(f"selftest expected two residuals, got {residual_names}")
        if len(manifest.get("groups", [])) != 1 or int(manifest["groups"][0].get("num_heads", 0)) != 2:
            raise RuntimeError("selftest shared-model manifest is invalid")
        log_file.write(f"shared model: {model_names[0]} · heads=2 · residuals=2\n")
        if include_exe:
            exe_names = [name for name in names if name.lower().endswith(".exe")]
            if not exe_names:
                raise RuntimeError("selftest bundle did not include the unified exe")
            log_file.write("bundled exe: " + ", ".join(exe_names) + "\n")
        log_file.write(
            f"SELFTEST_OK bundle={summary['bundle']} bytes={summary['bundle_bytes']} output={outputs[0]}\n"
        )


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("--selftest", "--selftest-full"):
        out_args = [arg for arg in sys.argv[2:] if not arg.startswith("--")]
        out = Path(out_args[0]) if out_args else Path.cwd() / "selftest_out"
        run_selftest(out, include_exe=sys.argv[1] == "--selftest-full")
        return 0

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    window = GlassWindow()
    paths = [str(Path(p).resolve()) for p in sys.argv[1:] if Path(p).exists()]
    zip_paths = [p for p in paths if Path(p).suffix.lower() == ".zip"]
    image_paths = [p for p in paths if Path(p).suffix.lower() in IMAGE_SUFFIXES]
    if zip_paths:
        window.switch_tab(1)
        window.receiver_page.set_bundle(zip_paths[0], auto_start=False)
    elif image_paths:
        window.sender_page._append_paths(image_paths)

    screen = app.primaryScreen().availableGeometry()
    width = min(1120, max(940, screen.width() - 48))
    height = min(820, max(680, screen.height() - 48))
    window.resize(width, height)
    window.move(
        screen.x() + max(0, (screen.width() - width) // 2),
        screen.y() + max(0, (screen.height() - height) // 2),
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

