#!/usr/bin/env python3
"""
VGOTEL - Full Screen Scanning Beam Animation with Blur Background (Windows)
Reduced timing – loader stays for 5 seconds total.
LED Dot-Matrix font, white beam sweeps across "V G O T E L".
Color: #2196F3 (blue)
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QFontDatabase

# Windows-specific blur
try:
    from PyQt5.QtWinExtras import QtWin
    WINDOWS_BLUR_AVAILABLE = True
except ImportError:
    WINDOWS_BLUR_AVAILABLE = False
    print("QtWinExtras not available. Blur effect disabled.")


class VgotelLoader(QWidget):
    finished = pyqtSignal()

    def __init__(self, duration=None, total_duration=5000, parent=None):
        """
        duration: for backward compatibility – if provided, overrides total_duration
        total_duration: total time loader stays on screen (ms) – default 5000 (5 sec)
        """
        super().__init__(parent)
        if duration is not None:
            total_duration = duration
        self.total_duration = total_duration
        self.beam_position = 0
        self.animation_step = 0
        self.animation_steps = 80          # fewer steps for shorter animation
        self.timer = None
        self.stage = 0
        self.setup_ui()
        self.load_custom_font()
        self.enable_background_blur()
        self.start_animation()
        print(f"[Loader] Started, will close after {self.total_duration} ms")

    def setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showFullScreen()

    def enable_background_blur(self):
        if WINDOWS_BLUR_AVAILABLE:
            self.setStyleSheet("background-color: rgba(33, 150, 243, 30);")
            QtWin.enableBlurBehindWindow(self)
        else:
            self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")

    def load_custom_font(self):
        possible_names = ["LED Dot-Matrix 400.ttf", "LED Dot-Matrix 400.otf", "LED Dot-Matrix 400"]
        font_path = None
        for name in possible_names:
            if os.path.exists(name):
                font_path = name
                break
        if font_path:
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    self.font_family = families[0]
                    return
        self.font_family = "Courier New"
        print("Warning: LED Dot-Matrix 400 font not found. Using Courier New.")

    def start_animation(self):
        # Reduced beam sweep time: 2 seconds (was 3.5)
        self.animation_duration = 2000
        self.idle_duration = self.total_duration - self.animation_duration
        if self.idle_duration < 0:
            self.idle_duration = 0
        self.step_time = max(1, self.animation_duration // self.animation_steps)
        self.animation_step = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(self.step_time)
        print(f"[Loader] Beam sweep: {self.animation_duration} ms, idle: {self.idle_duration} ms")

    def animate(self):
        if self.stage == 0:
            self.animation_step += 1
            if self.animation_step >= self.animation_steps:
                self.stage = 1
                self.timer.stop()
                print("[Loader] Beam sweep finished. Idle period starts...")
                if self.idle_duration > 0:
                    QTimer.singleShot(self.idle_duration, self.close_loader)
                else:
                    self.close_loader()
            else:
                self.beam_position = int((self.animation_step / self.animation_steps) * self.width())
                self.update()
        else:
            pass

    def close_loader(self):
        print("[Loader] Closing loader and emitting finished signal.")
        self.finished.emit()
        self.close()

    def finish(self):
        """External call – ignored to prevent early closing."""
        print("[Loader] External finish() ignored – loader will close only after full duration.")
        pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        font = QFont(self.font_family, 72, QFont.Bold)
        font.setLetterSpacing(QFont.PercentageSpacing, 90)
        painter.setFont(font)
        text = "V G O T E L"
        metrics = painter.fontMetrics()
        text_rect = metrics.boundingRect(text)
        text_rect.moveCenter(self.rect().center())

        x = text_rect.x()
        y = text_rect.y() + metrics.ascent()
        is_animating = (self.stage == 0 and self.timer and self.timer.isActive())
        base_color = QColor(33, 150, 243)

        for ch in text:
            char_width = metrics.width(ch)
            char_center = x + char_width / 2

            if is_animating:
                distance = abs(char_center - self.beam_position)
                if distance < 50:
                    color = QColor(255, 255, 255)
                else:
                    color = base_color
            else:
                color = base_color

            painter.setPen(color)
            painter.drawText(x, y, ch)
            x += char_width

        if is_animating:
            beam_x = self.beam_position - 50
            line_y = text_rect.bottom() - 10
            painter.setPen(QColor(255, 255, 255, 180))
            painter.drawLine(max(0, beam_x), line_y, min(self.width(), beam_x + 100), line_y)

        painter.end()


def show_loader_and_run(app, main_window_class, *args, **kwargs):
    """
    Shows the loader for its full duration (default 5 sec), then shows main window.
    """
    loader = VgotelLoader(total_duration=5000)   # 5 seconds
    loader.show()
    app.processEvents()

    def on_loader_finished():
        print("Loader finished – now creating and showing main window.")
        main_window = main_window_class(*args, **kwargs)
        main_window.show()

    loader.finished.connect(on_loader_finished)
    return loader


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loader = VgotelLoader(total_duration=5000)
    loader.show()
    sys.exit(app.exec_())