# custom_dialogs.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect, QApplication
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QRect, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath, QPen, QLinearGradient, QBrush


class ModernMessageBox(QDialog):
    """Ultra-Professional Custom Message Box with Modern Design"""
    
    def __init__(self, title, message, msg_type="info", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        
        self.title = title
        self.message = message
        self.msg_type = msg_type
        self.drag_position = None
        
        self.setup_ui()
        
        # Center the dialog on parent or screen
        self.center_dialog()
        
        self.show_enter_animation()
        
        # Auto-close timer for success messages
        if msg_type == "success":
            QTimer.singleShot(2500, self.accept)
    
    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
        
        # Color schemes for different message types
        self.colors = {
            "success": {
                "primary": "#10B981",
                "secondary": "#059669",
                "light": "#D1FAE5",
                "gradient_start": "#10B981",
                "gradient_end": "#059669",
                "icon": "✓",
            },
            "error": {
                "primary": "#EF4444",
                "secondary": "#DC2626",
                "light": "#FEE2E2",
                "gradient_start": "#EF4444",
                "gradient_end": "#DC2626",
                "icon": "✕",
            },
            "warning": {
                "primary": "#F59E0B",
                "secondary": "#D97706",
                "light": "#FEF3C7",
                "gradient_start": "#F59E0B",
                "gradient_end": "#D97706",
                "icon": "⚠",
            },
            "info": {
                "primary": "#3B82F6",
                "secondary": "#2563EB",
                "light": "#DBEAFE",
                "gradient_start": "#3B82F6",
                "gradient_end": "#2563EB",
                "icon": "ℹ",
            },
            "question": {
                "primary": "#8B5CF6",
                "secondary": "#7C3AED",
                "light": "#EDE9FE",
                "gradient_start": "#8B5CF6",
                "gradient_end": "#7C3AED",
                "icon": "?",
            }
        }
        
        color_scheme = self.colors.get(self.msg_type, self.colors["info"])
        
        # Main card
        self.card = QFrame()
        self.card.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.98);
                border-radius: 28px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        self.card.setLayout(card_layout)
        
        # Top gradient bar
        top_bar = QFrame()
        top_bar.setFixedHeight(6)
        top_bar.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color_scheme['gradient_start']},
                    stop:1 {color_scheme['gradient_end']});
                border-radius: 28px 28px 0 0;
            }}
        """)
        card_layout.addWidget(top_bar)
        
        # Content container
        content_widget = QFrame()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 25, 30, 30)
        content_layout.setSpacing(20)
        content_widget.setLayout(content_layout)
        
        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        
        # Icon container
        icon_container = QFrame()
        icon_container.setFixedSize(60, 60)
        r = int(color_scheme['primary'][1:3], 16)
        g = int(color_scheme['primary'][3:5], 16)
        b = int(color_scheme['primary'][5:7], 16)
        icon_container.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color_scheme['light']},
                    stop:1 rgba(255, 255, 255, 0.8));
                border-radius: 20px;
                border: 1px solid rgba({r}, {g}, {b}, 0.2);
            }}
        """)
        icon_layout = QVBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_container.setLayout(icon_layout)
        
        icon_label = QLabel(color_scheme['icon'])
        icon_label.setStyleSheet(f"""
            font-size: 32px;
            font-weight: bold;
            color: {color_scheme['primary']};
            background: transparent;
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        header_layout.addWidget(icon_container)
        
        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: 800;
            color: #1F2937;
            background: transparent;
            font-family: 'Segoe UI', 'SF Pro Display';
            letter-spacing: -0.3px;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 0.05);
                color: #6B7280;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.1);
                color: #1F2937;
            }
            QPushButton:pressed {
                background: rgba(0, 0, 0, 0.15);
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)
        
        content_layout.addLayout(header_layout)
        
        # Message
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            font-size: 14px;
            color: #4B5563;
            background: transparent;
            padding: 5px 0px;
            line-height: 1.6;
            font-family: 'Segoe UI';
        """)
        message_label.setMinimumWidth(380)
        content_layout.addWidget(message_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()
        
        # Primary button
        primary_btn = QPushButton("Confirm" if self.msg_type == "question" else "Got it")
        primary_btn.setCursor(Qt.PointingHandCursor)
        primary_btn.setMinimumSize(110, 44)
        primary_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color_scheme['gradient_start']},
                    stop:1 {color_scheme['gradient_end']});
                color: white;
                border: none;
                border-radius: 14px;
                font-weight: 700;
                font-size: 13px;
                font-family: 'Segoe UI';
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color_scheme['gradient_end']},
                    stop:1 {color_scheme['gradient_start']});
            }}
            QPushButton:pressed {{
                padding-top: 2px;
            }}
        """)
        primary_btn.clicked.connect(self.accept)
        button_layout.addWidget(primary_btn)
        
        # Secondary button for question type
        if self.msg_type == "question":
            secondary_btn = QPushButton("Cancel")
            secondary_btn.setCursor(Qt.PointingHandCursor)
            secondary_btn.setMinimumSize(110, 44)
            secondary_btn.setStyleSheet("""
                QPushButton {
                    background: white;
                    color: #6B7280;
                    border: 1.5px solid #E5E7EB;
                    border-radius: 14px;
                    font-weight: 600;
                    font-size: 13px;
                    font-family: 'Segoe UI';
                }
                QPushButton:hover {
                    background: #F9FAFB;
                    border-color: #D1D5DB;
                    color: #374151;
                }
                QPushButton:pressed {
                    background: #F3F4F6;
                }
            """)
            secondary_btn.clicked.connect(self.reject)
            button_layout.addWidget(secondary_btn)
        
        button_layout.addStretch()
        content_layout.addLayout(button_layout)
        
        card_layout.addWidget(content_widget)
        
        main_layout.addWidget(self.card)
        
        # Calculate size AFTER adding all widgets
        self.card.adjustSize()
        dialog_width = self.card.sizeHint().width() + 40
        dialog_height = self.card.sizeHint().height() + 40
        
        # Set fixed size
        self.setFixedSize(dialog_width, dialog_height)
    
    def center_dialog(self):
        """Center the dialog on parent or screen"""
        # Process events to ensure proper size calculation
        QApplication.processEvents()
        
        # Get the parent widget or screen geometry
        if self.parent():
            parent_geo = self.parent().geometry()
            parent_center = parent_geo.center()
            x = parent_center.x() - self.width() // 2
            y = parent_center.y() - self.height() // 2
        else:
            screen_geo = QApplication.primaryScreen().availableGeometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
        
        self.move(x, y)
    
    def mousePressEvent(self, event):
        """Handle window dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle window dragging"""
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Reset drag position"""
        self.drag_position = None
    
    def show_enter_animation(self):
        """Animate dialog entrance"""
        self.setWindowOpacity(0)
        
        # Opacity animation
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(250)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(1)
        self.opacity_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.opacity_anim.start()
        
        # Scale animation (instead of position bounce)
        self.setGraphicsEffect(None)
        
        # Simple bounce effect using geometry
        current_geo = self.geometry()
        start_geo = QRect(current_geo.x() + 20, current_geo.y() + 20, 
                          current_geo.width(), current_geo.height())
        self.setGeometry(start_geo)
        
        self.geo_anim = QPropertyAnimation(self, b"geometry")
        self.geo_anim.setDuration(350)
        self.geo_anim.setStartValue(start_geo)
        self.geo_anim.setEndValue(current_geo)
        self.geo_anim.setEasingCurve(QEasingCurve.OutElastic)
        self.geo_anim.start()
    
    @staticmethod
    def show_info(parent, title, message):
        dialog = ModernMessageBox(title, message, "info", parent)
        return dialog.exec_()
    
    @staticmethod
    def show_success(parent, title, message):
        dialog = ModernMessageBox(title, message, "success", parent)
        return dialog.exec_()
    
    @staticmethod
    def show_error(parent, title, message):
        dialog = ModernMessageBox(title, message, "error", parent)
        return dialog.exec_()
    
    @staticmethod
    def show_warning(parent, title, message):
        dialog = ModernMessageBox(title, message, "warning", parent)
        return dialog.exec_()
    
    @staticmethod
    def show_question(parent, title, message):
        dialog = ModernMessageBox(title, message, "question", parent)
        return dialog.exec_()


# For backward compatibility
CustomMessageBox = ModernMessageBox


class ToastNotification(QFrame):
    """Modern Toast Notification for non-blocking alerts"""
    
    def __init__(self, message, msg_type="info", parent=None, duration=3000):
        super().__init__(parent)
        self.message = message
        self.msg_type = msg_type
        self.duration = duration
        self.setup_ui()
        self.show_animation()
        
    def setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        colors = {
            "success": "#10B981",
            "error": "#EF4444", 
            "warning": "#F59E0B",
            "info": "#3B82F6"
        }
        
        icons = {
            "success": "✓",
            "error": "✕",
            "warning": "⚠",
            "info": "ℹ"
        }
        
        color = colors.get(self.msg_type, colors["info"])
        icon = icons.get(self.msg_type, "ℹ")
        
        self.setStyleSheet(f"""
            QFrame {{
                background: #1F2937;
                border-radius: 12px;
                border-left: 4px solid {color};
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 12, 20, 12)
        layout.setSpacing(12)
        self.setLayout(layout)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")
        layout.addWidget(icon_label)
        
        message_label = QLabel(self.message)
        message_label.setStyleSheet("color: white; font-size: 13px; font-family: 'Segoe UI';")
        layout.addWidget(message_label)
        
        layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #9CA3AF;
                border: none;
                font-size: 11px;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        close_btn.clicked.connect(self.hide_animation)
        layout.addWidget(close_btn)
        
        self.adjustSize()
        
        # Position at bottom-right of parent
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(parent_rect.width() - self.width() - 20, 
                     parent_rect.height() - self.height() - 20)
    
    def show_animation(self):
        self.setWindowOpacity(0)
        
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()
        
        QTimer.singleShot(self.duration, self.hide_animation)
    
    def hide_animation(self):
        self.anim_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_out.setDuration(300)
        self.anim_out.setStartValue(1)
        self.anim_out.setEndValue(0)
        self.anim_out.setEasingCurve(QEasingCurve.InCubic)
        self.anim_out.finished.connect(self.deleteLater)
        self.anim_out.start()
    
    @staticmethod
    def show(parent, message, msg_type="info", duration=3000):
        toast = ToastNotification(message, msg_type, parent, duration)
        toast.show()
        return toast


# Test code
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    
    # Test different message types
    ModernMessageBox.show_info(None, "Information", "This is an info message that will be centered on screen!")
    ModernMessageBox.show_success(None, "Success", "Operation completed successfully!")
    ModernMessageBox.show_warning(None, "Warning", "Please check your input!")
    ModernMessageBox.show_error(None, "Error", "Something went wrong!")
    ModernMessageBox.show_question(None, "Confirm", "Are you sure you want to proceed?")
    
    sys.exit(app.exec_())