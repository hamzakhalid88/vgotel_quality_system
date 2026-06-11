from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QDialog, QLineEdit, QComboBox, QCheckBox,
    QLabel, QFrame, QGridLayout, QGroupBox, QHeaderView,
    QMenu, QAbstractItemView, QProgressBar, QStatusBar,
    QToolButton, QFormLayout, QTreeWidget, QTreeWidgetItem,
    QSplitter, QScrollArea, QGraphicsDropShadowEffect, QDesktopWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QColor, QBrush, QFont, QPainter, QPixmap, QLinearGradient, QPen, QPalette
from database import Database
from config import ROLES
import re
from functools import partial
from typing import Dict, List


# ─────────────────────────────────────────────
#  GLOBAL DESIGN TOKENS
# ─────────────────────────────────────────────
COLORS = {
    "primary":        "#1A56DB",
    "primary_dark":   "#1245B8",
    "primary_light":  "#EBF2FF",
    "secondary":      "#0EA5E9",
    "accent":         "#7C3AED",
    "success":        "#10B981",
    "success_light":  "#D1FAE5",
    "warning":        "#F59E0B",
    "warning_light":  "#FEF3C7",
    "danger":         "#EF4444",
    "danger_light":   "#FEE2E2",
    "surface":        "#FFFFFF",
    "surface_alt":    "#F8FAFC",
    "border":         "#E2E8F0",
    "border_focus":   "#1A56DB",
    "text_primary":   "#0F172A",
    "text_secondary": "#475569",
    "text_muted":     "#94A3B8",
    "header_grad_1":  "#0F2557",
    "header_grad_2":  "#1A56DB",
}

FONT_FAMILY = "Segoe UI"

BASE_QSS = f"""
    QWidget {{
        font-family: '{FONT_FAMILY}', 'SF Pro Display', Arial;
        color: {COLORS['text_primary']};
    }}
    QLineEdit {{
        padding: 10px 14px;
        border: 1.5px solid {COLORS['border']};
        border-radius: 10px;
        background: {COLORS['surface']};
        font-size: 13px;
        color: {COLORS['text_primary']};
        min-height: 20px;
        selection-background-color: {COLORS['primary_light']};
    }}
    QLineEdit:focus {{
        border-color: {COLORS['border_focus']};
        background: #FAFCFF;
    }}
    QLineEdit:read-only {{
        background: {COLORS['surface_alt']};
        color: {COLORS['text_secondary']};
    }}
    QLineEdit[error="true"] {{
        border-color: {COLORS['danger']};
        background: #FFF5F5;
    }}
    QComboBox {{
        padding: 10px 14px;
        border: 1.5px solid {COLORS['border']};
        border-radius: 10px;
        background: {COLORS['surface']};
        font-size: 13px;
        color: {COLORS['text_primary']};
        min-height: 20px;
    }}
    QComboBox:focus {{
        border-color: {COLORS['border_focus']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    QComboBox::down-arrow {{
        image: none;
        width: 0; height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {COLORS['text_secondary']};
    }}
    QComboBox QAbstractItemView {{
        border: 1.5px solid {COLORS['border']};
        border-radius: 10px;
        background: white;
        selection-background-color: {COLORS['primary_light']};
        selection-color: {COLORS['primary']};
        padding: 4px;
        outline: 0;
    }}
    QCheckBox {{
        spacing: 10px;
        font-size: 13px;
        color: {COLORS['text_primary']};
    }}
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border: 2px solid {COLORS['border']};
        border-radius: 5px;
        background: white;
    }}
    QCheckBox::indicator:checked {{
        background: {COLORS['primary']};
        border-color: {COLORS['primary']};
        image: none;
    }}
    QCheckBox::indicator:hover {{
        border-color: {COLORS['primary']};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['border']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
    }}
    QScrollBar::handle:horizontal {{
        background: {COLORS['border']};
        border-radius: 4px;
        min-width: 30px;
    }}
    QToolTip {{
        background: {COLORS['text_primary']};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}
"""


def make_shadow(radius=16, x=0, y=4, color="#00000018"):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(radius)
    shadow.setOffset(x, y)
    shadow.setColor(QColor(color))
    return shadow


def styled_button(text, style="primary", size="md"):
    btn = QPushButton(text)
    sizes = {"sm": (32, "11px", "8px 14px"),
             "md": (40, "13px", "10px 20px"),
             "lg": (46, "14px", "12px 28px")}
    h, fs, pad = sizes.get(size, sizes["md"])
    btn.setFixedHeight(h)

    styles = {
        "primary": f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
                color: white; border: none; border-radius: 10px;
                font-size: {fs}; font-weight: 700; padding: {pad};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {COLORS['primary_dark']}, stop:1 {COLORS['primary']});
            }}
            QPushButton:pressed {{ padding-top: 11px; }}
        """,
        "success": f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #059669, stop:1 {COLORS['success']});
                color: white; border: none; border-radius: 10px;
                font-size: {fs}; font-weight: 700; padding: {pad};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #047857, stop:1 #059669);
            }}
        """,
        "danger": f"""
            QPushButton {{
                background: {COLORS['danger_light']};
                color: {COLORS['danger']}; border: 1.5px solid #FECACA;
                border-radius: 10px; font-size: {fs}; font-weight: 700; padding: {pad};
            }}
            QPushButton:hover {{
                background: {COLORS['danger']}; color: white;
                border-color: {COLORS['danger']};
            }}
        """,
        "ghost": f"""
            QPushButton {{
                background: {COLORS['surface_alt']};
                color: {COLORS['text_secondary']}; border: 1.5px solid {COLORS['border']};
                border-radius: 10px; font-size: {fs}; font-weight: 600; padding: {pad};
            }}
            QPushButton:hover {{
                background: {COLORS['border']};
                color: {COLORS['text_primary']};
            }}
        """,
        "teal": f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #0891B2, stop:1 #06B6D4);
                color: white; border: none; border-radius: 10px;
                font-size: {fs}; font-weight: 700; padding: {pad};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #0E7490, stop:1 #0891B2);
            }}
        """,
    }
    btn.setStyleSheet(styles.get(style, styles["primary"]))
    btn.setCursor(Qt.PointingHandCursor)
    return btn


# ─────────────────────────────────────────────
#  CLICKABLE LABEL
# ─────────────────────────────────────────────
class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


# ─────────────────────────────────────────────
#  UTILITY: CENTER DIALOG ON SCREEN
# ─────────────────────────────────────────────
def center_and_fit_dialog(dialog, margin=40):
    """Resize dialog to fit available screen geometry and center it."""
    screen = QDesktopWidget().availableGeometry(dialog)
    desired = dialog.size()
    new_width = min(desired.width(), screen.width() - margin)
    new_height = min(desired.height(), screen.height() - margin)
    dialog.resize(new_width, new_height)
    rect = dialog.geometry()
    rect.moveCenter(screen.center())
    dialog.setGeometry(rect)


# ─────────────────────────────────────────────
#  USER DIALOG  (Create / Edit)
# ─────────────────────────────────────────────
class UserDialog(QDialog):
    user_saved = pyqtSignal(dict)

    def __init__(self, db: Database, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.pwd_toggle = QPushButton()  # placeholder, will be recreated
        self.confirm_toggle = QPushButton()
        self.setup_ui()
        self.setup_validations()
        if user_data:
            self.load_user_data()
            self.setWindowTitle("Edit User Profile")
        else:
            self.setWindowTitle("Create New User")

        # Professional window placement & sizing
        center_and_fit_dialog(self, margin=40)

    # ────────────── UI CONSTRUCTION (single, clean version) ──────────────
    def setup_ui(self):
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(BASE_QSS + f"QDialog {{ background: {COLORS['surface_alt']}; }}")

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ---------- Header ----------
        header = self._create_header()
        root.addWidget(header)

        # ---------- Scroll Area (ensures scrolling) ----------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        body = QWidget()
        body.setStyleSheet(f"background: {COLORS['surface_alt']};")
        body_layout = QVBoxLayout(body)
        body_layout.setSpacing(22)
        body_layout.setContentsMargins(28, 24, 28, 24)

        # Account Details Card
        body_layout.addWidget(self._section_label("Account Details", "Basic profile information"))
        account_card = self._create_card()
        self._setup_account_grid(account_card)
        body_layout.addWidget(account_card)

        # Security Card
        body_layout.addWidget(self._section_label("Security Settings", "Password and account status"))
        security_card = self._create_card()
        self._setup_security_grid(security_card)
        body_layout.addWidget(security_card)

        # Tip Banner (edit mode)
        if self.user_data:
            body_layout.addWidget(self._create_tip_banner())

        body_layout.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)   # scroll area takes all extra space

        # ---------- Footer ----------
        footer = self._create_footer()
        root.addWidget(footer)

        # Signals
        self.pwd_toggle.toggled.connect(self.toggle_password)
        self.confirm_toggle.toggled.connect(self.toggle_confirm)

        # Tab order
        self._set_tab_order()

    # ────────────── Helper methods (clean, no duplication) ──────────────
    def _create_header(self):
        header = QFrame()
        header.setFixedHeight(68)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {COLORS['header_grad_1']}, stop:1 {COLORS['header_grad_2']});
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(28, 0, 28, 0)
        hl.setSpacing(16)

        avatar = QLabel("U")
        avatar.setFixedSize(42, 42)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("background: rgba(255,255,255,0.2); color: white; border-radius: 21px; font-weight:800; font-size:20px;")
        hl.addWidget(avatar)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(1)
        t1 = QLabel("User Management")
        t1.setStyleSheet("color:white; font-size:16px; font-weight:700; background:transparent;")
        t2 = QLabel("Edit Profile" if self.user_data else "Create New Account")
        t2.setStyleSheet("color:rgba(255,255,255,0.6); font-size:12px; background:transparent;")
        title_layout.addWidget(t1)
        title_layout.addWidget(t2)
        hl.addLayout(title_layout)
        hl.addStretch()

        badge = QLabel("EDITING" if self.user_data else "NEW")
        badge.setStyleSheet(f"""
            color: {'#FDE68A' if self.user_data else '#6EE7B7'};
            background: rgba(255,255,255,0.12);
            padding: 4px 14px; border-radius: 20px;
            font-size: 11px; font-weight: 800; letter-spacing: 1.5px;
        """)
        hl.addWidget(badge)
        return header

    def _create_card(self):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border: 1.5px solid {COLORS['border']};
                border-radius: 16px;
            }}
        """)
        card.setGraphicsEffect(make_shadow(24, 0, 4, "#00000010"))
        return card

    def _section_label(self, title, subtitle=""):
        frame = QFrame()
        frame.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"font-size:15px; font-weight:700; color:{COLORS['text_primary']};")
        layout.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setStyleSheet(f"font-size:12px; color:{COLORS['text_muted']};")
            layout.addWidget(s)
        return frame

    def _setup_account_grid(self, card):
        grid = QGridLayout(card)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(14)
        grid.setContentsMargins(24, 24, 24, 24)

        # Username
        self.username = QLineEdit()
        self.username.setPlaceholderText("e.g., john.doe")
        if self.user_data:
            self.username.setReadOnly(True)
        self._add_field_to_grid(grid, "Username *", self.username, 0, 0)

        # Full name
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Full legal name")
        self._add_field_to_grid(grid, "Full Name *", self.full_name, 0, 1)

        # Email with badge
        email_wrap, self.email, self.email_status = self._create_badge_input()
        self.email.setPlaceholderText("user@example.com")
        self._add_field_to_grid(grid, "Email Address", email_wrap, 1, 0)

        # Phone with badge
        phone_wrap, self.phone, self.phone_status = self._create_badge_input()
        self.phone.setPlaceholderText("+92 300 1234567")
        self._add_field_to_grid(grid, "Phone Number", phone_wrap, 1, 1)

        # Role
        self.role = QComboBox()
        for txt, val in [("Administrator", "admin"), ("Manager", "manager"),
                         ("Inspector", "inspector"), ("Viewer", "viewer")]:
            self.role.addItem(txt, val)
        self._add_field_to_grid(grid, "Role *", self.role, 2, 0)

        # Department
        self.department = QComboBox()
        self.department.addItems(["Quality Control", "Quality Assurance", "Production",
                                  "Maintenance", "R&D", "Management", "IT", "Logistics"])
        self.department.setEditable(True)
        self._add_field_to_grid(grid, "Department", self.department, 2, 1)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

    def _setup_security_grid(self, card):
        grid = QGridLayout(card)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)
        grid.setContentsMargins(24, 24, 24, 24)

        # Password with eye button
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Leave blank to keep current" if self.user_data else "Min. 6 characters")
        pwd_wrap, self.pwd_toggle = self._create_password_widget(self.password)
        self._add_to_sec_grid(grid, "New Password", pwd_wrap, 0)

        # Strength meter
        self.pwd_strength_bar = QProgressBar()
        self.pwd_strength_bar.setRange(0, 4)
        self.pwd_strength_bar.setValue(0)
        self.pwd_strength_bar.setTextVisible(False)
        self.pwd_strength_bar.setFixedHeight(6)
        self.pwd_strength_bar.setStyleSheet(f"""
            QProgressBar {{ background:{COLORS['border']}; border-radius:3px; border:none; }}
            QProgressBar::chunk {{ background:{COLORS['border']}; border-radius:3px; }}
        """)
        self.pwd_strength_label = QLabel("")
        self.pwd_strength_label.setStyleSheet(f"font-size:12px; font-weight:600; color:{COLORS['text_muted']};")
        strength_widget = QWidget()
        s_layout = QVBoxLayout(strength_widget)
        s_layout.setContentsMargins(0, 4, 0, 0)
        s_layout.setSpacing(5)
        s_layout.addWidget(self.pwd_strength_bar)
        s_layout.addWidget(self.pwd_strength_label)
        grid.addWidget(strength_widget, 1, 1, 1, 2)

        # Confirm password
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.confirm_password.setPlaceholderText("Re-enter password")
        confirm_wrap, self.confirm_toggle = self._create_password_widget(self.confirm_password)
        self._add_to_sec_grid(grid, "Confirm Password", confirm_wrap, 2)

        # Hint
        hint = QLabel("Minimum 6 characters. Use uppercase, numbers and symbols for a stronger password.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"""
            color:{COLORS['text_muted']}; font-size:12px;
            background:{COLORS['surface_alt']}; border-radius:8px; padding:8px 12px;
            border:1px solid {COLORS['border']};
        """)
        grid.addWidget(hint, 3, 1, 1, 2)

        # Active status
        status_card = QFrame()
        status_card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['success_light']};
                border: 1.5px solid #A7F3D0; border-radius: 10px;
            }}
        """)
        stl = QHBoxLayout(status_card)
        stl.setContentsMargins(14, 10, 14, 10)
        self.is_active = QCheckBox("Account Active — user can log in and access the system")
        self.is_active.setChecked(True)
        self.is_active.setStyleSheet(f"""
            QCheckBox {{ color:#065F46; font-weight:600; font-size:13px; spacing:10px; }}
            QCheckBox::indicator {{
                width:20px; height:20px;
                border:2px solid #059669; border-radius:6px; background:white;
            }}
            QCheckBox::indicator:checked {{
                background:{COLORS['success']}; border-color:{COLORS['success']};
            }}
        """)
        stl.addWidget(self.is_active)
        self._add_to_sec_grid(grid, "Account Status", status_card, 4)

        grid.setColumnStretch(1, 3)

    def _create_badge_input(self):
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        h = QHBoxLayout(wrap)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        inp = QLineEdit()
        badge = QLabel("")
        badge.setFixedSize(22, 22)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("font-size:14px; background:transparent;")
        h.addWidget(inp)
        h.addWidget(badge)
        return wrap, inp, badge

    def _create_password_widget(self, line_edit):
        widget = QWidget()
        widget.setStyleSheet("background:transparent;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        toggle_btn = QPushButton("Show")
        toggle_btn.setCheckable(True)
        toggle_btn.setFixedSize(52, 36)
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background:{COLORS['primary_light']}; color:{COLORS['primary']};
                border:1.5px solid #BFDBFE; border-radius:8px;
                font-size:11px; font-weight:700;
            }}
            QPushButton:checked {{
                background:{COLORS['primary']}; color:white;
                border-color:{COLORS['primary']};
            }}
        """)
        toggle_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(line_edit)
        layout.addWidget(toggle_btn)
        return widget, toggle_btn

    def _add_field_to_grid(self, grid, label_text, widget, row, col):
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"font-size:12px; font-weight:600; color:{COLORS['text_secondary']};")
        base_row = row * 3
        grid.addWidget(lbl, base_row, col * 2, 1, 1)
        grid.addWidget(widget, base_row + 1, col * 2, 1, 1)

    def _add_to_sec_grid(self, grid, label_text, widget, row):
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"font-size:12px; font-weight:600; color:{COLORS['text_secondary']};")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(lbl, row, 0, 1, 1)
        grid.addWidget(widget, row, 1, 1, 2)

    def _create_tip_banner(self):
        tip = QFrame()
        tip.setStyleSheet(f"""
            QFrame {{
                background: #EFF6FF;
                border: 1.5px solid #BFDBFE; border-radius: 12px;
            }}
        """)
        tl = QHBoxLayout(tip)
        tl.setContentsMargins(16, 12, 16, 12)
        tl.setSpacing(12)
        ico = QLabel("i")
        ico.setFixedSize(28, 28)
        ico.setAlignment(Qt.AlignCenter)
        ico.setStyleSheet(f"""
            background:{COLORS['primary']}; color:white;
            border-radius:14px; font-weight:800; font-size:13px;
        """)
        ttxt = QLabel("Leave the password fields empty to keep the existing password unchanged.")
        ttxt.setStyleSheet(f"color:{COLORS['primary_dark']}; font-size:12px; font-weight:500;")
        tl.addWidget(ico)
        tl.addWidget(ttxt, 1)
        return tip

    def _create_footer(self):
        footer = QFrame()
        footer.setFixedHeight(72)
        footer.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-top: 1.5px solid {COLORS['border']};
            }}
        """)
        ftl = QHBoxLayout(footer)
        ftl.setContentsMargins(28, 0, 28, 0)
        ftl.setSpacing(12)
        ftl.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedSize(110, 42)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background:{COLORS['surface_alt']}; color:{COLORS['text_secondary']};
                border:1.5px solid {COLORS['border']}; border-radius:10px;
                font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{COLORS['border']}; color:{COLORS['text_primary']}; }}
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Save User")
        self.save_btn.setFixedSize(154, 42)
        self.save_btn.setDefault(True)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #059669, stop:1 {COLORS['success']});
                color: white; border: none; border-radius: 10px;
                font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #047857, stop:1 #059669);
            }}
        """)
        self.save_btn.clicked.connect(self.validate_and_accept)

        ftl.addWidget(self.cancel_btn)
        ftl.addWidget(self.save_btn)
        return footer

    def _set_tab_order(self):
        widgets = [self.username, self.full_name, self.email, self.phone,
                   self.role, self.department, self.password, self.confirm_password,
                   self.is_active, self.save_btn, self.cancel_btn]
        for i in range(len(widgets)-1):
            self.setTabOrder(widgets[i], widgets[i+1])

    # ────────────── VALIDATION & DATA METHODS ──────────────
    def toggle_password(self, checked):
        self.password.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.pwd_toggle.setText("Hide" if checked else "Show")

    def toggle_confirm(self, checked):
        self.confirm_password.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.confirm_toggle.setText("Hide" if checked else "Show")

    def setup_validations(self):
        self.email.textChanged.connect(self.validate_email)
        self.phone.textChanged.connect(self.validate_phone)
        self.password.textChanged.connect(self.check_password_strength)
        self.confirm_password.textChanged.connect(self.check_password_match)
        self.username.textChanged.connect(self.check_username_availability)

    def load_user_data(self):
        self.username.setText(str(self.user_data.get('username', '')))
        self.full_name.setText(str(self.user_data.get('full_name', '')))
        self.email.setText(str(self.user_data.get('email', '')))
        self.phone.setText(str(self.user_data.get('phone', '')))
        role = self.user_data.get('role', 'viewer')
        idx = self.role.findData(role)
        if idx >= 0: self.role.setCurrentIndex(idx)
        dept = self.user_data.get('department', 'Quality Control')
        idx_d = self.department.findText(str(dept))
        if idx_d >= 0: self.department.setCurrentIndex(idx_d)
        else: self.department.setEditText(str(dept))
        self.is_active.setChecked(bool(self.user_data.get('is_active', True)))

    def validate_email(self):
        email = self.email.text().strip()
        if not email:
            self.email_status.setText(""); return True
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            self.email_status.setText("!"); self.email_status.setToolTip("Invalid email"); return False
        if not self.user_data or email != self.user_data.get('email'):
            existing = self.db.get_user_by_email(email) if hasattr(self.db, 'get_user_by_email') else None
            if existing:
                self.email_status.setText("X"); self.email_status.setToolTip("Already in use"); return False
        self.email_status.setText("OK"); self.email_status.setToolTip("Valid")
        self.email_status.setStyleSheet(f"color:{COLORS['success']}; font-size:11px; font-weight:700;")
        return True

    def validate_phone(self):
        phone = self.phone.text().strip()
        if not phone:
            self.phone_status.setText(""); return True
        if not re.match(r'^(\+92|0)?[0-9]{10,12}$', phone):
            self.phone_status.setText("!")
            self.phone_status.setToolTip("Example: +923001234567"); return False
        self.phone_status.setText("OK")
        self.phone_status.setStyleSheet(f"color:{COLORS['success']}; font-size:11px; font-weight:700;")
        return True

    def check_username_availability(self):
        if self.user_data: return True
        username = self.username.text().strip()
        if len(username) < 3:
            self.username.setStyleSheet(f"border:1.5px solid {COLORS['border']};"); return False
        existing = self.db.get_user_by_username(username) if hasattr(self.db, 'get_user_by_username') else None
        if existing:
            self.username.setStyleSheet(f"border:1.5px solid {COLORS['danger']};"); return False
        self.username.setStyleSheet(f"border:1.5px solid {COLORS['success']};"); return True

    def check_password_strength(self):
        pwd = self.password.text()
        s = 0
        if len(pwd) >= 8: s += 1
        if re.search(r'[A-Z]', pwd): s += 1
        if re.search(r'[0-9]', pwd): s += 1
        if re.search(r'[\W_]', pwd): s += 1
        self.pwd_strength_bar.setValue(s)
        colors = [COLORS['border'], COLORS['danger'], COLORS['warning'], COLORS['success'], "#059669"]
        self.pwd_strength_bar.setStyleSheet(f"""
            QProgressBar {{ background:{COLORS['border']}; border-radius:3px; border:none; }}
            QProgressBar::chunk {{ background:{colors[s]}; border-radius:3px; }}
        """)
        labels = ["", "Weak", "Fair", "Good", "Strong"]
        self.pwd_strength_label.setText(labels[s])
        self.pwd_strength_label.setStyleSheet(f"font-size:12px; font-weight:700; color:{colors[s]};")

    def check_password_match(self):
        if self.confirm_password.text() and self.password.text() != self.confirm_password.text():
            self.confirm_password.setStyleSheet(f"border:1.5px solid {COLORS['danger']};")
        else:
            self.confirm_password.setStyleSheet("")

    def validate_and_accept(self):
        if not self.user_data:
            if not self.username.text().strip():
                QMessageBox.warning(self, "Validation", "Username is required."); return
            if len(self.username.text().strip()) < 3:
                QMessageBox.warning(self, "Validation", "Username must be at least 3 characters."); return
            if not self.check_username_availability():
                QMessageBox.warning(self, "Validation", "Username already exists."); return
        if not self.full_name.text().strip():
            QMessageBox.warning(self, "Validation", "Full name is required."); return
        if not self.validate_email():
            QMessageBox.warning(self, "Validation", "Invalid or duplicate email."); return
        if not self.validate_phone():
            QMessageBox.warning(self, "Validation", "Invalid phone number format."); return
        if not self.user_data:
            pwd = self.password.text()
            if not pwd: QMessageBox.warning(self, "Validation", "Password is required."); return
            if len(pwd) < 6: QMessageBox.warning(self, "Validation", "Password too short (min 6 chars)."); return
            if pwd != self.confirm_password.text(): QMessageBox.warning(self, "Validation", "Passwords do not match."); return
        else:
            pwd = self.password.text()
            if pwd:
                if len(pwd) < 6: QMessageBox.warning(self, "Validation", "Password too short."); return
                if pwd != self.confirm_password.text(): QMessageBox.warning(self, "Validation", "Passwords do not match."); return
        self.accept()

    def get_user_data(self):
        data = {
            'full_name': self.full_name.text().strip(),
            'email': self.email.text().strip(),
            'phone': self.phone.text().strip(),
            'role': self.role.currentData(),
            'department': self.department.currentText().strip(),
            'is_active': self.is_active.isChecked()
        }
        if not self.user_data:
            data['username'] = self.username.text().strip()
            data['password'] = self.password.text()
        elif self.password.text():
            data['password'] = self.password.text()
        return data


# ─────────────────────────────────────────────
#  PERMISSION MANAGER DIALOG
# ─────────────────────────────────────────────
class PermissionManagerDialog(QDialog):
    permissions_saved = pyqtSignal(int)

    def __init__(self, db: Database, user_id: int, username: str, full_name: str,
                 current_admin_id: int = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.current_admin_id = current_admin_id
        self.permission_widgets = {}
        self.page_checkboxes = {}

        self.setWindowTitle(f"Permissions — {full_name}")
        self.setMinimumSize(800, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(BASE_QSS + f"QDialog {{ background:{COLORS['surface_alt']}; }}")

        self.setup_ui()
        self.load_data()

        # Professional placement
        center_and_fit_dialog(self, margin=40)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # HEADER
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {COLORS['header_grad_1']}, stop:1 {COLORS['accent']});
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(16)

        # User avatar initials
        initials = "".join([w[0].upper() for w in self.full_name.split()[:2]])
        av = QLabel(initials)
        av.setFixedSize(48, 48)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet("""
            background: rgba(255,255,255,0.25); color: white;
            border-radius: 24px; font-weight: 800; font-size: 18px;
        """)
        hl.addWidget(av)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        t1 = QLabel(self.full_name)
        t1.setStyleSheet("color:white; font-size:16px; font-weight:700; background:transparent;")
        t2 = QLabel(f"@{self.username}  •  ID #{self.user_id}")
        t2.setStyleSheet("color:rgba(255,255,255,0.6); font-size:12px; background:transparent;")
        text_col.addWidget(t1); text_col.addWidget(t2)
        hl.addLayout(text_col)
        hl.addStretch()

        user = self.db.get_user_by_id(self.user_id)
        role_txt = user.get('role', 'viewer').upper() if user else 'VIEWER'
        role_colors = {
            "ADMIN": ("#FEF3C7", "#D97706"),
            "MANAGER": ("#DBEAFE", "#1A56DB"),
            "INSPECTOR": ("#D1FAE5", "#059669"),
            "VIEWER": ("#F3F4F6", "#6B7280"),
        }
        rc, rt = role_colors.get(role_txt, ("#F3F4F6", "#6B7280"))
        role_badge = QLabel(role_txt)
        role_badge.setStyleSheet(f"""
            background:{rc}; color:{rt};
            padding:6px 16px; border-radius:20px;
            font-weight:800; font-size:11px; letter-spacing:1.5px;
        """)
        hl.addWidget(role_badge)
        root.addWidget(header)

        # INSTRUCTION STRIP
        tip_strip = QFrame()
        tip_strip.setStyleSheet(f"""
            QFrame {{
                background: #F0FDF4;
                border-bottom: 1.5px solid #BBF7D0;
            }}
        """)
        tip_strip.setFixedHeight(38)
        tsl = QHBoxLayout(tip_strip)
        tsl.setContentsMargins(24, 0, 24, 0)
        tip_lbl = QLabel(
            "Check to grant access  —  Uncheck to revoke  —  Admins always have full access"
        )
        tip_lbl.setStyleSheet(f"color:#065F46; font-size:12px; font-weight:500;")
        tsl.addWidget(tip_lbl)
        root.addWidget(tip_strip)

        # SCROLL AREA
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent; border:none;")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet(f"background:{COLORS['surface_alt']};")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(14)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setContentsMargins(20, 16, 20, 16)
        scroll.setWidget(self.scroll_content)
        root.addWidget(scroll, 1)

        # FOOTER
        footer = QFrame()
        footer.setFixedHeight(68)
        footer.setStyleSheet(f"""
            QFrame {{
                background:{COLORS['surface']};
                border-top: 1.5px solid {COLORS['border']};
            }}
        """)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.setSpacing(10)

        # Left side: utility buttons
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setFixedHeight(36)
        self.select_all_btn.setStyleSheet(f"""
            QPushButton {{
                background:{COLORS['primary_light']}; color:{COLORS['primary']};
                border:1.5px solid #BFDBFE; border-radius:8px;
                font-size:12px; font-weight:700; padding:0 14px;
            }}
            QPushButton:hover {{ background:#DBEAFE; }}
        """)
        self.select_all_btn.setCursor(Qt.PointingHandCursor)
        self.select_all_btn.clicked.connect(self.select_all)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.setFixedHeight(36)
        self.deselect_all_btn.setStyleSheet(f"""
            QPushButton {{
                background:{COLORS['surface_alt']}; color:{COLORS['text_secondary']};
                border:1.5px solid {COLORS['border']}; border-radius:8px;
                font-size:12px; font-weight:700; padding:0 14px;
            }}
            QPushButton:hover {{ background:{COLORS['border']}; }}
        """)
        self.deselect_all_btn.setCursor(Qt.PointingHandCursor)
        self.deselect_all_btn.clicked.connect(self.deselect_all)

        self.reset_role_btn = QPushButton("Reset to Role Default")
        self.reset_role_btn.setFixedHeight(36)
        self.reset_role_btn.setToolTip("Restore default permissions for this user's role")
        self.reset_role_btn.setStyleSheet(f"""
            QPushButton {{
                background:{COLORS['warning_light']}; color:#92400E;
                border:1.5px solid #FDE68A; border-radius:8px;
                font-size:12px; font-weight:700; padding:0 14px;
            }}
            QPushButton:hover {{ background:#FEF3C7; }}
        """)
        self.reset_role_btn.setCursor(Qt.PointingHandCursor)
        self.reset_role_btn.clicked.connect(self.reset_to_role_default)

        fl.addWidget(self.select_all_btn)
        fl.addWidget(self.deselect_all_btn)
        fl.addWidget(self.reset_role_btn)
        fl.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedSize(110, 42)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background:{COLORS['surface_alt']}; color:{COLORS['text_secondary']};
                border:1.5px solid {COLORS['border']}; border-radius:10px;
                font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{COLORS['border']}; }}
        """)
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)

        self.save_btn = QPushButton("Save Permissions")
        self.save_btn.setFixedSize(160, 42)
        self.save_btn.setDefault(True)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {COLORS['primary_dark']}, stop:1 {COLORS['primary']});
                color:white; border:none; border-radius:10px;
                font-size:13px; font-weight:700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #0D3A9E, stop:1 {COLORS['primary_dark']});
            }}
        """)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_permissions)

        fl.addWidget(self.cancel_btn)
        fl.addWidget(self.save_btn)
        root.addWidget(footer)

    def create_page_card(self, page_data: Dict, user_permissions: List[Dict]):
        page_id    = page_data['page_id']
        page_name  = page_data['page_name']
        page_icon  = page_data.get('icon', '')
        functions  = page_data.get('functions', [])

        # Outer card
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border: 1.5px solid {COLORS['border']};
                border-radius: 14px;
            }}
        """)
        card.setGraphicsEffect(make_shadow(16, 0, 3, "#00000010"))

        cl = QVBoxLayout(card)
        cl.setSpacing(10)
        cl.setContentsMargins(0, 0, 0, 0)

        # Card header bar
        header_bar = QFrame()
        header_bar.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface_alt']};
                border-bottom: 1.5px solid {COLORS['border']};
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            }}
        """)
        header_bar.setFixedHeight(44)
        hbl = QHBoxLayout(header_bar)
        hbl.setContentsMargins(18, 0, 18, 0)
        hbl.setSpacing(10)

        page_title = QLabel(f"{page_icon}  {page_name}" if page_icon else page_name)
        page_title.setStyleSheet(f"font-size:14px; font-weight:700; color:{COLORS['text_primary']};")
        hbl.addWidget(page_title)
        hbl.addStretch()

        route_lbl = QLabel(page_data.get('route', ''))
        route_lbl.setStyleSheet(f"font-size:11px; color:{COLORS['text_muted']}; font-family:Consolas,monospace;")
        hbl.addWidget(route_lbl)

        master_checkbox = QCheckBox("Full Access")
        master_checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-size:12px; font-weight:700;
                color:{COLORS['success']}; spacing:7px;
            }}
            QCheckBox::indicator {{
                width:18px; height:18px;
                border:2px solid {COLORS['success']}; border-radius:5px; background:white;
            }}
            QCheckBox::indicator:checked {{
                background:{COLORS['success']}; border-color:{COLORS['success']};
            }}
        """)
        master_checkbox.stateChanged.connect(
            lambda state, pid=page_id: self.on_master_changed(pid, state))
        self.page_checkboxes[page_id] = master_checkbox
        hbl.addWidget(master_checkbox)

        cl.addWidget(header_bar)

        # Functions row
        func_widget = QWidget()
        func_widget.setStyleSheet("background:transparent;")
        func_layout = QHBoxLayout(func_widget)
        func_layout.setSpacing(8)
        func_layout.setContentsMargins(18, 6, 18, 14)

        for func in functions:
            func_id   = func['function_id']
            func_name = func['function_name']
            func_code = func['code']

            pill = QFrame()
            pill.setStyleSheet(f"""
                QFrame {{
                    background: {COLORS['surface_alt']};
                    border: 1.5px solid {COLORS['border']};
                    border-radius: 20px;
                }}
            """)
            pill_layout = QHBoxLayout(pill)
            pill_layout.setContentsMargins(10, 4, 14, 4)
            pill_layout.setSpacing(6)

            checkbox = QCheckBox(func_name)
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    font-size:12px; font-weight:500; color:{COLORS['text_primary']}; spacing:6px;
                }}
                QCheckBox::indicator {{
                    width:15px; height:15px;
                    border:2px solid {COLORS['border']}; border-radius:4px; background:white;
                }}
                QCheckBox::indicator:checked {{
                    background:{COLORS['primary']}; border-color:{COLORS['primary']};
                }}
            """)
            checkbox.setToolTip(f"Code: {func_code}\n{func.get('description', '')}")
            pill_layout.addWidget(checkbox)

            func_key = f"func_{page_id}_{func_id}"
            self.permission_widgets[func_key] = checkbox
            func_layout.addWidget(pill)

        if not functions:
            no_func = QLabel("No granular functions defined")
            no_func.setStyleSheet(f"color:{COLORS['text_muted']}; font-size:12px; font-style:italic;")
            func_layout.addWidget(no_func)

        func_layout.addStretch()
        cl.addWidget(func_widget)

        # Set initial checkbox states
        page_allowed = any(
            p['page_id'] == page_id and p['is_allowed']
            for p in user_permissions
        )
        master_checkbox.setChecked(page_allowed)

        for func in functions:
            func_id  = func['function_id']
            func_key = f"func_{page_id}_{func_id}"
            is_ok = any(
                p['page_id'] == page_id and p['function_id'] == func_id and p['is_allowed']
                for p in user_permissions
            )
            if func_key in self.permission_widgets:
                self.permission_widgets[func_key].setChecked(is_ok)

        self.scroll_layout.addWidget(card)

    def on_master_changed(self, page_id: int, state: int):
        checked = (state == Qt.Checked)
        for key, cb in self.permission_widgets.items():
            if key.startswith(f"func_{page_id}_"):
                cb.setChecked(checked)

    def load_data(self):
        try:
            self.db.initialize_default_pages()
            pages     = self.db.get_all_pages_with_functions()
            user_perms = self.db.get_user_permissions(self.user_id)
            for page in pages:
                self.create_page_card(page, user_perms)
            self.scroll_layout.addStretch()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load permissions:\n{str(e)}")

    def select_all(self):
        for cb in self.page_checkboxes.values(): cb.setChecked(True)
        for cb in self.permission_widgets.values(): cb.setChecked(True)

    def deselect_all(self):
        for cb in self.page_checkboxes.values(): cb.setChecked(False)
        for cb in self.permission_widgets.values(): cb.setChecked(False)

    def reset_to_role_default(self):
        r = QMessageBox.question(self, "Confirm Reset",
                                 "Reset permissions to role defaults?\nCurrent changes will be lost.",
                                 QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            user = self.db.get_user_by_id(self.user_id)
            if user:
                self.db.apply_role_permissions(self.user_id, user.get('role', 'viewer'))
                self.clear_layout(); self.load_data()
                QMessageBox.information(self, "Done", "Permissions reset to role defaults.")

    def clear_layout(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.permission_widgets.clear(); self.page_checkboxes.clear()

    def save_permissions(self):
        permissions = []
        for key, cb in self.permission_widgets.items():
            if key.startswith("func_"):
                parts = key.split("_")
                permissions.append({
                    'user_id':     self.user_id,
                    'page_id':     int(parts[1]),
                    'function_id': int(parts[2]),
                    'is_allowed':  cb.isChecked()
                })
        try:
            ok = self.db.save_user_permissions(self.user_id, permissions, self.current_admin_id)
            if ok:
                self.permissions_saved.emit(self.user_id)
                QMessageBox.information(self, "Saved", "Permissions saved successfully.")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to save permissions.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{str(e)}")


# ─────────────────────────────────────────────
#  USERS WIDGET  (Main Page)
# ─────────────────────────────────────────────
class UsersWidget(QWidget):

    def __init__(self, db: Database, user_role: str, current_user_id: int = None):
        super().__init__()
        self.db = db
        self.user_role = user_role
        self.current_user_id = current_user_id
        self.all_users = []
        self.displayed_user_ids = []
        self.setup_ui()
        self.load_users()

    def setup_ui(self):
        self.setStyleSheet(BASE_QSS + f"""
            QWidget {{ background: {COLORS['surface_alt']}; }}
        """)

        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # ── HEADER CARD ──────────────────────
        header_card = QFrame()
        header_card.setFixedHeight(80)
        header_card.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {COLORS['header_grad_1']},
                    stop:0.6 {COLORS['header_grad_2']},
                    stop:1 {COLORS['secondary']});
                border-radius: 18px;
            }}
        """)
        header_card.setGraphicsEffect(make_shadow(28, 0, 6, "#1A56DB30"))

        hl = QHBoxLayout(header_card)
        hl.setContentsMargins(28, 0, 28, 0)
        hl.setSpacing(16)

        icon_bg = QLabel("T")
        icon_bg.setFixedSize(46, 46)
        icon_bg.setAlignment(Qt.AlignCenter)
        icon_bg.setStyleSheet("""
            background: rgba(255,255,255,0.18);
            border-radius: 23px; color: white;
            font-weight: 800; font-size: 20px;
        """)
        hl.addWidget(icon_bg)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        t1 = QLabel("Team Management")
        t1.setStyleSheet("color:white; font-size:20px; font-weight:800; background:transparent;")
        t2 = QLabel("Manage users, roles and system permissions")
        t2.setStyleSheet("color:rgba(255,255,255,0.65); font-size:12px; background:transparent;")
        title_col.addWidget(t1); title_col.addWidget(t2)
        hl.addLayout(title_col)
        hl.addStretch()

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("""
            color: white;
            background: rgba(255,255,255,0.18);
            padding: 6px 16px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
        """)
        hl.addWidget(self.stats_label)

        root.addWidget(header_card)

        # ── CONTROL BAR ──────────────────────
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border: 1.5px solid {COLORS['border']};
                border-radius: 14px;
            }}
        """)
        ctrl_card.setGraphicsEffect(make_shadow(14, 0, 2, "#00000008"))

        ctrl_layout = QHBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(18, 12, 18, 12)
        ctrl_layout.setSpacing(12)

        # Search
        search_container = QFrame()
        search_container.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface_alt']};
                border: 1.5px solid {COLORS['border']};
                border-radius: 10px;
            }}
        """)
        scl = QHBoxLayout(search_container)
        scl.setContentsMargins(12, 0, 12, 0)
        scl.setSpacing(8)
        search_icon = QLabel("S")
        search_icon.setStyleSheet(f"color:{COLORS['text_muted']}; font-weight:700; font-size:13px;")
        scl.addWidget(search_icon)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, username or email...")
        self.search_input.setStyleSheet("""
            QLineEdit { border: none; background: transparent; font-size: 13px; }
        """)
        self.search_input.textChanged.connect(self.filter_users)
        scl.addWidget(self.search_input)
        search_container.setMinimumWidth(260)

        ctrl_layout.addWidget(search_container, 2)

        # Divider
        div = QFrame(); div.setFrameShape(QFrame.VLine)
        div.setStyleSheet(f"color:{COLORS['border']};")
        ctrl_layout.addWidget(div)

        self.role_filter = QComboBox()
        self.role_filter.addItem("All Roles", "all")
        for r in ["admin", "manager", "inspector", "viewer"]:
            self.role_filter.addItem(r.capitalize(), r)
        self.role_filter.setFixedWidth(140)
        self.role_filter.currentIndexChanged.connect(self.filter_users)
        ctrl_layout.addWidget(self.role_filter)

        self.dept_filter = QComboBox()
        self.dept_filter.addItem("All Depts.", "all")
        for dept in ["Quality Control", "Quality Assurance", "Production",
                     "Maintenance", "R&D", "Management", "IT", "Logistics"]:
            self.dept_filter.addItem(dept, dept)
        self.dept_filter.setFixedWidth(160)
        self.dept_filter.currentIndexChanged.connect(self.filter_users)
        ctrl_layout.addWidget(self.dept_filter)

        div2 = QFrame(); div2.setFrameShape(QFrame.VLine)
        div2.setStyleSheet(f"color:{COLORS['border']};")
        ctrl_layout.addWidget(div2)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setFixedHeight(38)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background:{COLORS['surface_alt']}; color:{COLORS['text_secondary']};
                border:1.5px solid {COLORS['border']}; border-radius:9px;
                font-size:13px; font-weight:600; padding:0 16px;
            }}
            QPushButton:hover {{ background:{COLORS['border']}; }}
        """)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_users)
        ctrl_layout.addWidget(self.refresh_btn)

        self.add_btn = QPushButton("+ New User")
        self.add_btn.setFixedHeight(38)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
                color:white; border:none; border-radius:9px;
                font-size:13px; font-weight:700; padding:0 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {COLORS['primary_dark']}, stop:1 {COLORS['primary']});
            }}
        """)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_user)
        ctrl_layout.addWidget(self.add_btn)

        root.addWidget(ctrl_card)

        # Loading bar
        self.loading_bar = QProgressBar()
        self.loading_bar.setVisible(False)
        self.loading_bar.setFixedHeight(3)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setStyleSheet(f"""
            QProgressBar {{ border-radius:2px; background:{COLORS['border']}; border:none; }}
            QProgressBar::chunk {{ background:{COLORS['primary']}; border-radius:2px; }}
        """)
        root.addWidget(self.loading_bar)

        # ── TABLE ────────────────────────────
        table_card = QFrame()
        table_card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border: 1.5px solid {COLORS['border']};
                border-radius: 16px;
            }}
        """)
        table_card.setGraphicsEffect(make_shadow(20, 0, 4, "#00000010"))
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(0)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(8)
        self.users_table.setHorizontalHeaderLabels(
            ["", "Username", "Full Name", "Email", "Role", "Status", "Last Login", "Actions"])
        self.users_table.setAlternatingRowColors(False)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.users_table.setSortingEnabled(True)
        self.users_table.setWordWrap(False)
        self.users_table.setShowGrid(False)
        self.users_table.setFrameShape(QFrame.NoFrame)

        hdr = self.users_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(7, QHeaderView.Fixed)
        self.users_table.setColumnWidth(0, 60)
        self.users_table.setColumnWidth(7, 160)
        self.users_table.verticalHeader().setVisible(False)

        self.users_table.setStyleSheet(f"""
            QTableWidget {{
                background: {COLORS['surface']};
                border: none;
                border-radius: 16px;
                font-size: 13px;
                outline: 0;
                gridline-color: transparent;
            }}
            QHeaderView::section {{
                background: {COLORS['surface_alt']};
                color: {COLORS['text_secondary']};
                padding: 0 14px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.8px;
                text-transform: uppercase;
                border: none;
                border-bottom: 2px solid {COLORS['border']};
                height: 42px;
            }}
            QHeaderView::section:first {{
                border-top-left-radius: 16px;
            }}
            QHeaderView::section:last {{
                border-top-right-radius: 16px;
            }}
            QTableWidget::item {{
                padding: 4px 10px;
                border-bottom: 1px solid #F1F5F9;
                color: {COLORS['text_primary']};
            }}
            QTableWidget::item:selected {{
                background: {COLORS['primary_light']};
                color: {COLORS['primary_dark']};
            }}
            QTableWidget::item:hover {{
                background: #F8FAFF;
            }}
        """)

        tc_layout.addWidget(self.users_table)
        root.addWidget(table_card, 1)

        self.users_table.doubleClicked.connect(self.on_double_click)
        self.users_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.users_table.customContextMenuRequested.connect(self.show_context_menu)

        # STATUS BAR
        self.status_bar = QStatusBar()
        self.status_bar.setFixedHeight(30)
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: transparent;
                color: {COLORS['text_muted']};
                font-size: 12px;
                border: none;
            }}
        """)
        self.status_bar.showMessage("Ready")
        root.addWidget(self.status_bar)

    # ── DATA METHODS ─────────────────────────
    def load_users(self):
        self.loading_bar.setVisible(True)
        self.loading_bar.setRange(0, 0)
        QTimer.singleShot(100, self._load_users_async)

    def _load_users_async(self):
        try:
            self.all_users = self.db.get_all_users()
            self.filter_users()
            active_count = sum(1 for u in self.all_users if u.get('is_active'))
            self.stats_label.setText(
                f"Total: {len(self.all_users)}    Active: {active_count}")
            self.status_bar.showMessage(f"Loaded {len(self.all_users)} users", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load users:\n{str(e)}")
        finally:
            self.loading_bar.setVisible(False)
            self.loading_bar.setRange(0, 100)

    def filter_users(self):
        search  = self.search_input.text().strip().lower()
        role_f  = self.role_filter.currentData()
        dept_f  = self.dept_filter.currentData()
        filtered = []
        for u in self.all_users:
            if role_f != "all" and u.get('role') != role_f: continue
            if dept_f != "all" and u.get('department') != dept_f: continue
            if search:
                if not any(search in str(u.get(k, '')).lower()
                           for k in ('username', 'full_name', 'email', 'role')):
                    continue
            filtered.append(u)
        self.display_users(filtered)

    def get_initials_avatar(self, full_name, size=36):
        initials = "".join([w[0].upper() for w in full_name.split()[:2]]).ljust(2, "?")[:2]
        palette  = ["#1A56DB", "#7C3AED", "#059669", "#DC2626",
                    "#D97706", "#0891B2", "#0F172A", "#BE185D"]
        color    = palette[hash(full_name) % len(palette)]
        px = QPixmap(size, size)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, size, size, size // 2, size // 2)
        p.setPen(QColor("white"))
        f = QFont(FONT_FAMILY, int(size * 0.38), QFont.Bold)
        p.setFont(f)
        p.drawText(px.rect(), Qt.AlignCenter, initials)
        p.end()
        return px

    def display_users(self, users):
        self.users_table.setRowCount(len(users))
        self.displayed_user_ids = [u.get('id') for u in users]
        self.users_table.verticalHeader().setDefaultSectionSize(56)
        self.users_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        for row, user in enumerate(users):
            # Avatar
            av = QLabel()
            px = self.get_initials_avatar(user.get('full_name', 'U'), 36)
            av.setPixmap(px)
            av.setAlignment(Qt.AlignCenter)
            av.setToolTip(user.get('full_name', ''))
            self.users_table.setCellWidget(row, 0, av)

            # Text cells
            for col, key in enumerate(['username', 'full_name', 'email'], start=1):
                item = QTableWidgetItem(str(user.get(key, '')))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.users_table.setItem(row, col, item)

            # Role badge cell
            role = str(user.get('role', 'viewer')).lower()
            role_colors_map = {
                "admin":     ("#FEF3C7", "#92400E", "#D97706"),
                "manager":   ("#DBEAFE", "#1E40AF", "#1A56DB"),
                "inspector": ("#D1FAE5", "#065F46", "#059669"),
                "viewer":    ("#F3F4F6", "#374151", "#6B7280"),
            }
            bg, fg, _ = role_colors_map.get(role, ("#F3F4F6", "#374151", "#6B7280"))
            role_item = QTableWidgetItem(role.capitalize())
            role_item.setForeground(QBrush(QColor(fg)))
            role_item.setBackground(QBrush(QColor(bg)))
            role_item.setFlags(role_item.flags() & ~Qt.ItemIsEditable)
            role_item.setTextAlignment(Qt.AlignCenter)
            self.users_table.setItem(row, 4, role_item)

            # Status
            is_active = user.get('is_active', False)
            st_item = QTableWidgetItem("Active" if is_active else "Inactive")
            st_item.setForeground(QBrush(QColor(COLORS['success'] if is_active else COLORS['danger'])))
            st_item.setBackground(QBrush(QColor(
                COLORS['success_light'] if is_active else COLORS['danger_light'])))
            st_item.setTextAlignment(Qt.AlignCenter)
            st_item.setFlags(st_item.flags() & ~Qt.ItemIsEditable)
            self.users_table.setItem(row, 5, st_item)

            # Last login
            ll = user.get('last_login')
            ll_str = str(ll)[:16] if ll else "Never logged in"
            ll_item = QTableWidgetItem(ll_str)
            ll_item.setForeground(QBrush(QColor(COLORS['text_muted'])))
            ll_item.setFlags(ll_item.flags() & ~Qt.ItemIsEditable)
            self.users_table.setItem(row, 6, ll_item)

            # Actions
            aw = QWidget()
            aw.setStyleSheet("background:transparent;")
            al = QHBoxLayout(aw)
            al.setContentsMargins(8, 8, 8, 8)
            al.setSpacing(6)

            def _action_btn(label, bg, fg, hover_bg, hover_fg="white"):
                b = QPushButton(label)
                b.setFixedSize(32, 32)
                b.setCursor(Qt.PointingHandCursor)
                b.setStyleSheet(f"""
                    QPushButton {{
                        background:{bg}; color:{fg};
                        border:none; border-radius:8px;
                        font-size:11px; font-weight:700;
                    }}
                    QPushButton:hover {{
                        background:{hover_bg}; color:{hover_fg};
                    }}
                """)
                return b

            # Permissions btn (admin only)
            perm_btn = _action_btn("P", COLORS['primary_light'], COLORS['primary'],
                                   COLORS['primary'])
            perm_btn.setToolTip("Manage Permissions")
            perm_btn.clicked.connect(
                partial(self.manage_permissions,
                        user.get('id'), user.get('username'), user.get('full_name')))
            if self.user_role != 'admin':
                perm_btn.setVisible(False)
            al.addWidget(perm_btn)

            # Edit btn
            edit_btn = _action_btn("E", "#EEF2FF", COLORS['primary'],
                                   COLORS['primary'])
            edit_btn.setToolTip("Edit User")
            edit_btn.clicked.connect(partial(self.edit_user, user.get('id')))
            al.addWidget(edit_btn)

            # Toggle btn
            toggle_lbl = "On" if not is_active else "Off"
            toggle_bg   = COLORS['success_light'] if not is_active else COLORS['warning_light']
            toggle_fg   = COLORS['success'] if not is_active else COLORS['warning']
            toggle_hbg  = COLORS['success'] if not is_active else COLORS['warning']
            toggle_btn  = _action_btn(toggle_lbl, toggle_bg, toggle_fg, toggle_hbg)
            toggle_btn.setToolTip("Activate" if not is_active else "Deactivate")
            toggle_btn.clicked.connect(partial(self.toggle_user_status, user.get('id'), is_active))
            al.addWidget(toggle_btn)

            # Delete btn
            del_btn = _action_btn("X", COLORS['danger_light'], COLORS['danger'],
                                  COLORS['danger'])
            del_btn.setToolTip("Delete User")
            del_btn.clicked.connect(partial(self.delete_user, user.get('id'), user.get('username')))
            al.addWidget(del_btn)
            al.addStretch()

            # Permission-based visibility
            if self.user_role != 'admin':
                del_btn.setVisible(False)
                if self.user_role == 'manager':
                    if user.get('role') == 'admin':
                        edit_btn.setVisible(False)
                        toggle_btn.setVisible(False)
                elif self.user_role in ['inspector', 'viewer']:
                    edit_btn.setVisible(False)
                    toggle_btn.setVisible(False)
            if self.current_user_id and user.get('id') == self.current_user_id:
                del_btn.setVisible(False)
                toggle_btn.setVisible(False)

            self.users_table.setCellWidget(row, 7, aw)

    # ── EVENT HANDLERS ───────────────────────
    def on_double_click(self, index):
        row = index.row()
        if row < 0: return
        uid  = self.displayed_user_ids[row]
        user = next((u for u in self.all_users if u.get('id') == uid), None)
        if user and self.user_role == 'manager' and user.get('role') == 'admin':
            QMessageBox.warning(self, "Access Denied", "Cannot edit administrators.")
            return
        self.edit_user(uid)

    def show_context_menu(self, position):
        row = self.users_table.rowAt(position.y())
        if row < 0: return
        uid  = self.displayed_user_ids[row]
        user = next((u for u in self.all_users if u.get('id') == uid), None)
        if not user: return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {COLORS['surface']};
                border: 1.5px solid {COLORS['border']};
                border-radius: 12px;
                padding: 6px;
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 8px;
                color: {COLORS['text_primary']};
            }}
            QMenu::item:selected {{
                background: {COLORS['primary_light']};
                color: {COLORS['primary']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {COLORS['border']};
                margin: 4px 10px;
            }}
        """)

        edit_action = menu.addAction("Edit User")
        edit_action.triggered.connect(lambda: self.edit_user(uid))

        if self.user_role == 'admin':
            perm_action = menu.addAction("Manage Permissions")
            perm_action.triggered.connect(
                lambda: self.manage_permissions(uid, user.get('username'), user.get('full_name')))
            menu.addSeparator()
            toggle_action = menu.addAction(
                "Deactivate User" if user.get('is_active') else "Activate User")
            toggle_action.triggered.connect(
                lambda: self.toggle_user_status(uid, user.get('is_active')))
            menu.addSeparator()
            delete_action = menu.addAction("Delete User")
            delete_action.triggered.connect(lambda: self.delete_user(uid, user.get('username')))

        elif self.user_role == 'manager' and user.get('role') != 'admin':
            menu.addSeparator()
            toggle_action = menu.addAction(
                "Deactivate User" if user.get('is_active') else "Activate User")
            toggle_action.triggered.connect(
                lambda: self.toggle_user_status(uid, user.get('is_active')))

        menu.exec_(self.users_table.viewport().mapToGlobal(position))

    # ── CRUD ACTIONS ─────────────────────────
    def manage_permissions(self, user_id: int, username: str, full_name: str):
        """Open permission manager for selected user"""
        if self.user_role != 'admin':
            QMessageBox.warning(self, "Access Denied",
                                "Only administrators can manage permissions.")
            return
        if self.current_user_id and user_id == self.current_user_id:
            QMessageBox.information(self, "Info",
                                    "As the current admin, you have full access automatically.")
            return
        dialog = PermissionManagerDialog(
            self.db, user_id, username, full_name,
            self.current_user_id, parent=self)
        dialog.permissions_saved.connect(
            lambda uid: self.status_bar.showMessage(
                f"Permissions updated for {full_name}", 3000))
        dialog.exec_()

    def add_user(self):
        if self.user_role not in ['admin', 'manager']:
            QMessageBox.warning(self, "Access Denied",
                                "You do not have permission to add users.")
            return
        dialog = UserDialog(self.db, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            user_data = dialog.get_user_data()
            user_data['created_by'] = self.current_user_id
            user_id = self.db.create_user(user_data)
            if user_id:
                self.load_users()
                self.status_bar.showMessage(
                    f"User '{user_data.get('username')}' created successfully.", 4000)
            else:
                QMessageBox.critical(self, "Error",
                                     "Failed to create user. Username may already exist.")

    def edit_user(self, user_id):
        if self.user_role not in ['admin', 'manager']:
            QMessageBox.warning(self, "Access Denied",
                                "You do not have permission to edit users.")
            return
        user = next((u for u in self.all_users if u.get('id') == user_id), None)
        if not user:
            QMessageBox.warning(self, "Error", "User not found."); return
        if self.user_role == 'manager' and user.get('role') == 'admin':
            QMessageBox.warning(self, "Access Denied",
                                "Managers cannot edit administrator accounts.")
            return
        dialog = UserDialog(self.db, user_data=user, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_user_data()
            if self.db.update_user(user_id, updated_data):
                self.load_users()
                self.status_bar.showMessage(
                    f"User '{user.get('username')}' updated successfully.", 3000)
            else:
                QMessageBox.critical(self, "Error", "Failed to update user.")

    def toggle_user_status(self, user_id, current_status):
        if self.user_role not in ['admin', 'manager']:
            QMessageBox.warning(self, "Access Denied",
                                "You do not have permission to change user status.")
            return
        user = next((u for u in self.all_users if u.get('id') == user_id), None)
        if not user: return
        if self.user_role == 'manager' and user.get('role') == 'admin':
            QMessageBox.warning(self, "Access Denied",
                                "Managers cannot change administrator status.")
            return
        new_status = not current_status
        action     = "activate" if new_status else "deactivate"

        reply = QMessageBox.question(
            self, "Confirm Action",
            f"Are you sure you want to {action} '{user.get('username')}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.db.update_user(user_id, {'is_active': new_status}):
                self.load_users()
                self.status_bar.showMessage(
                    f"User '{user.get('username')}' {action}d successfully.", 3000)
            else:
                QMessageBox.critical(self, "Error", "Failed to update user status.")

    def delete_user(self, user_id, username):
        if self.user_role != 'admin':
            QMessageBox.warning(self, "Access Denied",
                                "Only administrators can delete users.")
            return
        if self.current_user_id and user_id == self.current_user_id:
            QMessageBox.warning(self, "Action Denied",
                                "You cannot delete your own account.")
            return

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Permanently delete user '{username}'?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.db.delete_user(user_id):
                self.load_users()
                self.status_bar.showMessage(
                    f"User '{username}' deleted permanently.", 4000)
            else:
                QMessageBox.critical(
                    self, "Error",
                    "Deletion failed. The user may have associated records in the system.")