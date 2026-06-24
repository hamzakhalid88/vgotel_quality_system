import sys
from datetime import datetime
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QLineEdit, QPushButton, QScrollArea,
    QGroupBox, QMessageBox, QComboBox, QTextEdit,
    QDateEdit, QTabWidget, QSpinBox, QApplication, QDialog,
    QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
    QButtonGroup, QRadioButton, QInputDialog  # <--- QInputDialog یہاں شامل کیا
)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon
from database import Database
from custom_dialogs import CustomMessageBox


class NewEntryWidget(QWidget):
    data_saved = pyqtSignal()

    # ---- Phone‑type fault dictionaries for Final Test (only used if station == Final) ----
    FEATURE_PHONE_FAULTS = {
        "📱 DISPLAY": ["LCD BLACK", "LCD WHITE", "LCD SHADE", "LCD SPOT", "LCD LINE", "LCD BUBBLE", "LCD BLING"],
        "🔊 AUDIO": ["RECEIVER NOT WORK", "RECEIVER DISTORTION", "RECEIVER SLOW", "RINGER NOT WORK", "RINGER DISTORTION", "RINGER SLOW", "MIC NOT WORK"],
        "📷 CAMERA": ["CAMERA BLACK/WHITE", "CAMERA ERROR", "CAMERA SHADE/SPOT/LINE", "CAMERA BLUR"],
        "💡 LED": ["TORCH NOT WORK", "ONE TORCH NOT WORK", "TORCH AUTO WORK", "FLASH NOT WORK", "FLASH AUTO WORK", "LCD DAMAGE"],
        "🔘 KEYPAD": ["KEYPAD NOT WORK", "KEYPAD WORK SOMETIME", "KEYPAD HARD", "KEYPAD AUTO WORK"],
        "⚡ POWER": ["DEAD", "AUTO OFF", "VIBRATOR NOT WORK", "VIBRATOR AUTO WORK", "HANDFREE LOGO"],
        "🔹 OTHERS": ["IMEI WITHOUT WRITE","IMEI WRONG WRITE","IMEI SAME WRITE","INSERT SIM"]
    }

    SMART_PHONE_FAULTS = {
        "📷 CAMERA": ["REAR CAMERA NOT WORK","FRONT CAMERA NOT WORK", "REAR CAMERA BLACK","FRONT CAMERA BLACK","CAMERA SHADE","CAMERA SPOT","DEP-FIELD CAM SUB"],
        "🔊 AUDIO": ["RECEIVER NOT WORK", "RECEIVER DISTORTION", "RINGER NOT WORK", "RINGER DISTORTION","AUDIO LOOP", "HEADSET","FM RADIO", "MIC NOT WORK"],
        "📱 DISPLAY": ["LCD BLACK", "LCD WHITE", "LCD SHADE", "LCD SPOT", "LCD LINE", "LCD BUBBLE", "LCD BLING"],
        "📡 SENSORS": ["PROXIMITY SENSOR FAIL", "AMBIENT LIGHT SENSOR FAIL", "GRAVITY SENSOR", "LIGHT SENSOR","M/S RANG SENSOR","FINGER PRINT","MAGNETIC SENSOR"],
        "💡 LED": ["TORCH NOT WORK", "ONE TORCH NOT WORK", "TORCH AUTO WORK", "FLASH NOT WORK", "FLASH AUTO WORK", "LCD DAMAGE"],
        "🌐 NETWORK": ["NO NETWORK", "WEAK SIGNAL", "WIFI NOT WORKING", "BLUETOOTH ISSUE", "GPS NOT WORKING","SIM/SD CARD"],
        "🔘 KEYPAD": ["KEYPAD NOT WORK", "KEYPAD WORK SOMETIME", "KEYPAD HARD", "KEYPAD AUTO WORK"],
        "⚡ POWER": ["DEAD", "AUTO OFF","SIDE KEY / POWER KEY", "VIBRATOR NOT WORK", "VIBRATOR AUTO WORK","HANG"],
        "🔹 OTHERS": ["IMEI WITHOUT WRITE","IMEI WRONG WRITE","IMEI SAME WRITE","INSERT SIM"]
    }

    def __init__(self, db: Database, user_data=None, edit_mode=False, edit_data=None):
        super().__init__()
        self.db = db
        self.user = user_data or {'full_name': 'Inspector', 'id': '001', 'role': 'inspector'}
        self.fault_inputs = {}
        self.edit_mode = edit_mode
        self.edit_data = edit_data
        self.edit_inspection_code = None
        self.save_btn = None
        self.category_widgets = {}
        self.rework_table = None
        self.setup_ui()

        if edit_mode and edit_data:
            self.load_edit_data()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #f5f7fa;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)

        content = QWidget()
        content.setStyleSheet("background: #f5f7fa;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(25, 20, 25, 20)
        content_layout.setSpacing(20)
        content.setLayout(content_layout)

        basic_info = self.create_basic_info_panel()
        content_layout.addWidget(basic_info)

        self.fault_panel = self.create_fault_panel()
        content_layout.addWidget(self.fault_panel, 2)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def create_top_bar(self):
        top_bar = QFrame()
        top_bar.setFixedHeight(85)
        top_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0f2027, stop:0.5 #203a43, stop:1 #2c5364);
                border-bottom: 3px solid #00b4d8;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(40, 0, 40, 0)
        top_bar.setLayout(layout)

        logo_container = QHBoxLayout()
        logo_container.setSpacing(10)
        logo_label = QLabel("🎯")
        logo_label.setStyleSheet("font-size: 32px;")
        logo_container.addWidget(logo_label)
        title_label = QLabel("QUALITY CONTROL SYSTEM")
        title_label.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        logo_container.addWidget(title_label)
        layout.addLayout(logo_container)
        layout.addStretch()

        datetime_container = QHBoxLayout()
        datetime_container.setSpacing(20)

        date_widget = QFrame()
        date_widget.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.15);
                border-radius: 10px;
                padding: 5px;
            }
        """)
        date_layout = QHBoxLayout()
        date_widget.setLayout(date_layout)
        date_icon = QLabel("📅")
        date_icon.setStyleSheet("font-size: 16px;")
        date_layout.addWidget(date_icon)
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setStyleSheet("""
            QDateEdit {
                background: transparent;
                color: white;
                border: none;
                font-size: 13px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        date_layout.addWidget(self.date_edit)
        datetime_container.addWidget(date_widget)

        time_widget = QFrame()
        time_widget.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.15);
                border-radius: 10px;
                padding: 5px;
            }
        """)
        time_layout = QHBoxLayout()
        time_widget.setLayout(time_layout)
        time_icon = QLabel("⏰")
        time_icon.setStyleSheet("font-size: 16px;")
        time_layout.addWidget(time_icon)
        self.time_label = QLabel()
        self.time_label.setStyleSheet("""
            color: white;
            font-size: 13px;
            font-weight: bold;
            font-family: monospace;
        """)
        time_layout.addWidget(self.time_label)
        datetime_container.addWidget(time_widget)
        layout.addLayout(datetime_container)
        layout.addStretch()

        station_widget = QFrame()
        station_widget.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.15);
                border-radius: 10px;
                padding: 5px;
            }
        """)
        station_layout = QHBoxLayout()
        station_widget.setLayout(station_layout)
        station_icon = QLabel("🏭")
        station_icon.setStyleSheet("font-size: 16px;")
        station_layout.addWidget(station_icon)
        self.station_combo = QComboBox()
        self.station_combo.addItems(["Semi Test", "MMI Test", "Appearance Test", "Final Test", "Rework"])
        self.station_combo.setStyleSheet("""
            QComboBox {
                background: transparent;
                color: white;
                border: none;
                font-size: 13px;
                font-weight: bold;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #203a43;
                color: white;
                selection-background-color: #00b4d8;
            }
        """)
        self.station_combo.currentTextChanged.connect(self.on_station_changed)
        station_layout.addWidget(self.station_combo)
        layout.addWidget(station_widget)

        self.update_time()
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)

        return top_bar

    def create_basic_info_panel(self):
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 15px;
                border: none;
            }
        """)
        panel.setGraphicsEffect(self.create_shadow())

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(20)
        panel.setLayout(layout)

        header_layout = QHBoxLayout()
        header = QLabel("📋 BASIC INFORMATION")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f2027;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        required_badge = QLabel("* All Fields Required")
        required_badge.setStyleSheet("""
            background: #ff6b6b;
            color: white;
            padding: 3px 10px;
            border-radius: 10px;
            font-size: 9px;
            font-weight: bold;
        """)
        header_layout.addWidget(required_badge)
        layout.addLayout(header_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background: #e0e0e0; max-height: 1px;")
        layout.addWidget(line)

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(20)

        model_widget = self.create_field_widget("📱 MODEL", self.create_styled_line_edit(), required=True)
        self.model_input = model_widget.findChild(QLineEdit)
        row1_layout.addWidget(model_widget)

        color_widget = self.create_field_widget("🎨 COLOR", self.create_styled_line_edit(), required=True)
        self.color_input = color_widget.findChild(QLineEdit)
        row1_layout.addWidget(color_widget)

        shipment_widget = self.create_field_widget("🚚 SHIPMENT", self.create_styled_line_edit(), required=True)
        self.shipment_input = shipment_widget.findChild(QLineEdit)
        row1_layout.addWidget(shipment_widget)

        employee_widget = self.create_field_widget("👤 EMPLOYEE NAME", self.create_styled_line_edit(), required=True)
        self.employee_input = employee_widget.findChild(QLineEdit)
        row1_layout.addWidget(employee_widget)

        layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(20)

        id_widget = self.create_field_widget("🆔 TESTER ID", self.create_styled_line_edit(), required=True)
        self.id_input = id_widget.findChild(QLineEdit)
        self.id_input.setText(str(self.user.get('id', '')))
        row2_layout.addWidget(id_widget)

        line_widget = self.create_field_widget("📍 LINE", self.create_styled_combo_box(), required=True)
        self.line_combo = line_widget.findChild(QComboBox)
        row2_layout.addWidget(line_widget)

        floor_widget = self.create_field_widget("🏭 FLOOR", self.create_styled_combo_box(), required=True)
        self.floor_combo = floor_widget.findChild(QComboBox)
        self.floor_combo.addItems(["2nd Floor", "3rd Floor"])
        self.floor_combo.setCurrentIndex(0)
        self.floor_combo.currentTextChanged.connect(self.on_floor_changed)
        row2_layout.addWidget(floor_widget)

        layout.addLayout(row2_layout)
        self.on_floor_changed("2nd Floor")

        # ========== PHONE TYPE ROW ==========
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(20)

        phone_type_widget = QWidget()
        phone_type_layout = QHBoxLayout()
        phone_type_layout.setContentsMargins(0, 0, 0, 0)
        phone_type_layout.setSpacing(10)

        phone_type_label = QLabel("📱 Phone Type:")
        phone_type_label.setStyleSheet("font-weight: bold; color: #4a5568; font-size: 11px;")
        phone_type_layout.addWidget(phone_type_label)

        self.phone_type_group = QButtonGroup(self)
        self.phone_type_group.setExclusive(True)

        self.feature_radio = QRadioButton("Feature Phone")
        self.feature_radio.setChecked(True)
        self.smart_radio = QRadioButton("Smart Phone")

        for rb in (self.feature_radio, self.smart_radio):
            rb.setStyleSheet("""
                QRadioButton {
                    font-weight: 600;
                    padding: 4px 12px;
                    background: white;
                    border: 2px solid #cbd5e0;
                    border-radius: 16px;
                    font-size: 11px;
                }
                QRadioButton:checked {
                    background: #00b4d8;
                    color: white;
                    border-color: #00b4d8;
                }
            """)
            phone_type_layout.addWidget(rb)
            self.phone_type_group.addButton(rb)

        self.feature_radio.toggled.connect(self.on_phone_type_changed)
        self.smart_radio.toggled.connect(self.on_phone_type_changed)

        phone_type_layout.addStretch()
        phone_type_widget.setLayout(phone_type_layout)
        row3_layout.addWidget(phone_type_widget)

        layout.addLayout(row3_layout)
        # =============================================

        return panel

    def create_fault_panel(self):
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 15px;
                border: none;
            }
        """)
        panel.setGraphicsEffect(self.create_shadow())
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        panel.setLayout(layout)

        header = QLabel("🔍 FAULT ENTRY")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f2027;")
        layout.addWidget(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background: #e0e0e0; max-height: 1px;")
        layout.addWidget(line)

        self.category_tabs = QTabWidget()
        self.category_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.category_tabs.setUsesScrollButtons(False)
        self.category_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                background: white;
                margin-top: -1px;
            }
            QTabBar::tab {
                background: #f1f5f9;
                color: #334155;
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: #00b4d8;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #e2e8f0;
            }
        """)
        layout.addWidget(self.category_tabs, 1)

        summary_group = QFrame()
        summary_group.setStyleSheet("""
            QFrame {
                background: #f7fafc;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        summary_layout = QVBoxLayout()
        summary_layout.setContentsMargins(15, 10, 15, 10)
        summary_layout.setSpacing(8)
        summary_group.setLayout(summary_layout)

        summary_header = QHBoxLayout()
        summary_title = QLabel("📊 FAULT SUMMARY")
        summary_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #0f2027;")
        summary_header.addWidget(summary_title)
        summary_header.addStretch()
        summary_layout.addLayout(summary_header)

        self.fault_summary_text = QTextEdit()
        self.fault_summary_text.setReadOnly(True)
        self.fault_summary_text.setMaximumHeight(80)
        self.fault_summary_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background: white;
                font-family: monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)
        summary_layout.addWidget(self.fault_summary_text)

        total_frame = QFrame()
        total_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff6b6b, stop:1 #ee5a24);
                border-radius: 8px;
            }
        """)
        total_layout = QHBoxLayout()
        total_layout.setContentsMargins(15, 10, 15, 10)
        total_frame.setLayout(total_layout)

        total_icon = QLabel("⚠️")
        total_icon.setStyleSheet("font-size: 20px;")
        total_layout.addWidget(total_icon)
        total_text = QLabel("Total Faulty Units:")
        total_text.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        total_layout.addWidget(total_text)
        self.total_faults_label = QLabel("0")
        self.total_faults_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        total_layout.addWidget(self.total_faults_label)
        total_layout.addStretch()

        summary_layout.addWidget(total_frame)
        layout.addWidget(summary_group)

        self.save_btn = QPushButton("💾 SAVE INSPECTION REPORT")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00b4d8, stop:1 #0077b6);
                color: white;
                border: none;
                padding: 12px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0096c7, stop:1 #023e8a);
            }
        """)
        self.save_btn.clicked.connect(self.save_inspection)
        layout.addWidget(self.save_btn)

        self.on_station_changed("Semi Test")
        return panel

    # ================== REWORK PANEL (DYNAMIC FROM DB) ==================
    def create_rework_panel(self, phone_type="Feature"):
        """Create rework table with faults from database based on phone_type."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        self.rework_table = QTableWidget()
        self.rework_table.setColumnCount(5)
        self.rework_table.setHorizontalHeaderLabels(["Fault Name", "PCB", "Material", "Fixing", "Solding"])
        self.rework_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rework_table.setAlternatingRowColors(True)

        self.rework_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rework_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rework_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.rework_table.cellChanged.connect(self.update_summary)

        self.rework_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #e2e8f0;
                background: white;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background: #f1f5f9;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.rework_table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Row")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        add_btn.clicked.connect(self.add_rework_row)
        remove_btn = QPushButton("🗑 Remove Selected Row")
        remove_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c82333;
            }
        """)
        remove_btn.clicked.connect(self.remove_rework_row)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Load faults from database
        self.load_rework_faults(phone_type)

        layout.addStretch()
        return widget

    def load_rework_faults(self, phone_type):
        """Load rework faults from database based on phone_type."""
        if self.rework_table is None:
            return
        self.rework_table.setRowCount(0)

        # Determine category name
        category_name = "Rework Smart" if phone_type == "Smart" else "Rework Feature"

        # Fetch category from DB
        cat = self.db.execute_query(
            "SELECT id FROM fault_categories WHERE category_name = ? AND station_type = 'Rework'",
            (category_name,), fetch_one=True
        )
        if not cat:
            faults = []
        else:
            faults_records = self.db.get_faults_by_category(cat['id'])
            faults = [f['fault_name'] for f in faults_records]

        if not faults:
            # If no faults, add a placeholder editable row
            self.add_rework_row()
            return

        # Populate table with fault names (read-only)
        for fault_name in faults:
            row = self.rework_table.rowCount()
            self.rework_table.insertRow(row)
            fault_item = QTableWidgetItem(fault_name)
            fault_item.setFlags(fault_item.flags() & ~Qt.ItemIsEditable)
            self.rework_table.setItem(row, 0, fault_item)
            for col in range(1, 5):
                self.rework_table.setItem(row, col, QTableWidgetItem(""))

        # Adjust height
        self.rework_table.resizeRowsToContents()
        row_height = self.rework_table.rowHeight(0) if self.rework_table.rowCount() > 0 else 30
        header_height = self.rework_table.horizontalHeader().height()
        min_height = header_height + self.rework_table.rowCount() * row_height + 20
        self.rework_table.setMinimumHeight(min_height)

    def add_rework_row(self):
        if self.rework_table is None:
            return
        row = self.rework_table.rowCount()
        self.rework_table.insertRow(row)
        fault_item = QTableWidgetItem("")
        fault_item.setFlags(fault_item.flags() | Qt.ItemIsEditable)
        self.rework_table.setItem(row, 0, fault_item)
        for col in range(1, 5):
            self.rework_table.setItem(row, col, QTableWidgetItem(""))

    def remove_rework_row(self):
        if self.rework_table is None:
            return
        current_row = self.rework_table.currentRow()
        if current_row >= 0:
            self.rework_table.removeRow(current_row)
    # =====================================================================

    # ================== MODIFIED: create_category_widget ==================
    def create_category_widget(self, fault_list, category_id=None):
        """
        fault_list: list of tuples (fault_id, fault_name)
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        cols = 2
        grid_layout = QGridLayout()
        grid_layout.setVerticalSpacing(15)
        grid_layout.setHorizontalSpacing(20)

        for idx, (fid, fname) in enumerate(fault_list):
            fault_card = self.create_fault_card(fname, fault_id=fid, category_id=category_id)
            row = idx // cols
            col = idx % cols
            grid_layout.addWidget(fault_card, row, col)

        layout.addLayout(grid_layout)
        layout.addStretch()
        return widget

    # ================== MODIFIED: create_fault_card ==================
    def create_fault_card(self, fault_name, fault_id=None, category_id=None):
        fault_card = QFrame()
        fault_card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
            }
            QFrame:hover {
                background: #f8fafc;
                border-color: #00b4d8;
            }
        """)
        fault_card.setMinimumHeight(60)
        fault_card.setMaximumHeight(70)

        fault_layout = QHBoxLayout()
        fault_layout.setContentsMargins(12, 8, 12, 8)
        fault_layout.setSpacing(12)
        fault_card.setLayout(fault_layout)

        label = QLabel(fault_name)
        label.setCursor(Qt.PointingHandCursor)  # ہاتھ کا کرسر
        label.setStyleSheet("""
            color: #1e293b;
            font-weight: 600;
            font-size: 13px;
            background: transparent;
        """)
        label.setWordWrap(True)
        # ڈبل کلک ایونٹ منسلک کریں
        label.mouseDoubleClickEvent = lambda event, f=fault_name, fid=fault_id, lbl=label: self.edit_fault_name(f, fid, lbl)
        fault_layout.addWidget(label, 2)

        spinbox = QSpinBox()
        spinbox.setRange(0, 9999)
        spinbox.setValue(0)
        spinbox.setSuffix(" pcs")
        spinbox.setMinimumWidth(110)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setStyleSheet("""
            QSpinBox {
                padding: 6px;
                border: 1px solid #cbd5e0;
                border-radius: 8px;
                background: white;
                font-size: 13px;
                font-weight: 500;
                min-width: 100px;
            }
            QSpinBox:focus {
                border-color: #00b4d8;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 22px;
            }
        """)
        spinbox.valueChanged.connect(self.update_summary)
        fault_layout.addWidget(spinbox)
        self.fault_inputs[fault_name] = spinbox
        return fault_card

    # ================== NEW: Edit Fault Name Function ==================
    def edit_fault_name(self, old_name, fault_id, label_widget):
        from PyQt5.QtWidgets import QInputDialog

        new_name, ok = QInputDialog.getText(self, "Edit Fault Name",
                                            "Enter new fault name:", text=old_name)
        if ok and new_name and new_name.strip():
            new_name = new_name.strip()
            if new_name == old_name:
                return  # کوئی تبدیلی نہیں

            # 1. لیبل اپ ڈیٹ کریں
            label_widget.setText(new_name)

            # 2. fault_inputs ڈکشنری اپ ڈیٹ کریں
            spinbox = self.fault_inputs.pop(old_name, None)
            if spinbox:
                self.fault_inputs[new_name] = spinbox

            # 3. سمری ریفریش کریں
            self.update_summary()

            # 4. اگر fault_id موجود ہے تو ڈیٹا بیس اپ ڈیٹ کریں
            if fault_id is not None:
                try:
                    # ڈیٹا بیس کنکشن حاصل کریں
                    conn = None
                    if hasattr(self.db, 'connection'):
                        conn = self.db.connection
                    elif hasattr(self.db, 'conn'):
                        conn = self.db.conn
                    elif hasattr(self.db, '_connection'):  # کچھ اور نام ہو سکتا ہے
                        conn = self.db._connection

                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE faults SET fault_name = ? WHERE id = ?", (new_name, fault_id))
                        conn.commit()
                        # (اختیاری) کامیابی کا پیغام
                        # CustomMessageBox.show_info(self, "Success", "Fault name updated in database.")
                    else:
                        # اگر کنکشن نہ ملے تو پھر بھی execute_query آزمائیں (اگر وہ UPDATE کو سپورٹ کرتی ہو)
                        self.db.execute_query(
                            "UPDATE faults SET fault_name = ? WHERE id = ?",
                            (new_name, fault_id)
                        )
                        # اگر execute_query خود commit نہ کرتی ہو تو manual commit کریں
                        if hasattr(self.db, 'commit'):
                            self.db.commit()
                        elif hasattr(self.db, 'connection') and hasattr(self.db.connection, 'commit'):
                            self.db.connection.commit()
                except Exception as e:
                    CustomMessageBox.show_error(self, "Database Error",
                                                f"Could not update fault name in database: {e}")

    # ================== Appearance Smart ==================
    def load_appearance_faults(self, phone_type):
        """Load appearance faults from database based on phone_type."""
        self.category_tabs.clear()
        self.fault_inputs.clear()

        # Category name based on phone type
        if phone_type == "Smart":
            category_name = "Appearance Smart"
        else:
            category_name = "APPEARANCE FAULTS"  # Feature

        # Fetch category from DB
        cat = self.db.execute_query(
            "SELECT id FROM fault_categories WHERE category_name = ? AND station_type = 'Appearance Test'",
            (category_name,), fetch_one=True
        )
        if not cat:
            # If no category, show a placeholder
            widget = self.create_category_widget([(None, "No faults loaded for this phone type")], "General")
            self.category_tabs.addTab(widget, "General")
            self.update_summary()
            return

        cat_id = cat['id']
        faults_records = self.db.get_faults_by_category(cat_id)
        fault_list = [(f['id'], f['fault_name']) for f in faults_records]

        if fault_list:
            widget = self.create_category_widget(fault_list, category_name)
            self.category_tabs.addTab(widget, category_name)
        else:
            widget = self.create_category_widget([(None, "No faults")], category_name)
            self.category_tabs.addTab(widget, category_name)

        self.update_summary()

    # ================== MMI Smart ==================
    def load_mmi_smart_faults(self):
        """Load all MMI Smart categories (each group as a separate tab)."""
        self.category_tabs.clear()
        self.fault_inputs.clear()
        categories = self.db.get_fault_categories("MMI Test", phone_type="Smart")
        if not categories:
            widget = self.create_category_widget([(None, "No Smart faults loaded")], "General")
            self.category_tabs.addTab(widget, "General")
            self.update_summary()
            return
        for cat in categories:
            cat_id = cat['id']
            cat_name = cat['category_name']
            faults_records = self.db.get_faults_by_category(cat_id)
            fault_list = [(f['id'], f['fault_name']) for f in faults_records]
            if fault_list:
                widget = self.create_category_widget(fault_list, cat_name)
                self.category_tabs.addTab(widget, cat_name)
            else:
                widget = self.create_category_widget([(None, "No faults")], cat_name)
                self.category_tabs.addTab(widget, cat_name)
        self.update_summary()

    # ================== Phone type change handler ==================
    def on_phone_type_changed(self):
        """Called when phone type radio buttons change"""
        station = self.station_combo.currentText()
        if station == "Rework":
            phone_type = "Smart" if self.smart_radio.isChecked() else "Feature"
            if self.category_tabs.count() > 0:
                self.category_tabs.removeTab(0)
            rework_panel = self.create_rework_panel(phone_type)
            self.category_tabs.addTab(rework_panel, "🔄 Rework Details")
            self.update_summary()
        elif station == "Final Test":
            current_type = "Feature" if self.feature_radio.isChecked() else "Smart"
            self.load_final_test_faults(current_type)
        elif station == "Appearance Test":
            phone_type = "Smart" if self.smart_radio.isChecked() else "Feature"
            self.load_appearance_faults(phone_type)
        elif station == "MMI Test":
            phone_type = "Smart" if self.smart_radio.isChecked() else "Feature"
            if phone_type == "Smart":
                self.load_mmi_smart_faults()
            else:
                self.load_default_faults(station, phone_type="Feature")

    def on_station_changed(self, station):
        if hasattr(self, 'category_tabs'):
            self.category_tabs.clear()
            self.fault_inputs.clear()
            if station == "Rework":
                phone_type = "Smart" if self.smart_radio.isChecked() else "Feature"
                rework_panel = self.create_rework_panel(phone_type)
                self.category_tabs.addTab(rework_panel, "🔄 Rework Details")
            elif station == "Final Test":
                current_type = "Feature" if self.feature_radio.isChecked() else "Smart"
                self.load_final_test_faults(current_type)
            elif station == "Appearance Test":
                phone_type = "Smart" if self.smart_radio.isChecked() else "Feature"
                self.load_appearance_faults(phone_type)
            elif station == "MMI Test":
                phone_type = "Smart" if self.smart_radio.isChecked() else "Feature"
                if phone_type == "Smart":
                    self.load_mmi_smart_faults()
                else:
                    self.load_default_faults(station, phone_type="Feature")
            else:
                self.load_default_faults(station)
            self.update_summary()

    # ================== MODIFIED: load_final_test_faults ==================
    def load_final_test_faults(self, phone_type):
        self.category_tabs.clear()
        self.fault_inputs.clear()
        faults_dict = self.FEATURE_PHONE_FAULTS if phone_type == "Feature" else self.SMART_PHONE_FAULTS
        for tab_name, fault_list in faults_dict.items():
            # چونکہ یہ ہارڈ کوڈڈ ہیں، ان کے پاس ID نہیں ہے، اس لیے None بھیجیں
            fault_list_with_ids = [(None, f) for f in fault_list]
            widget = self.create_category_widget(fault_list_with_ids)
            self.category_tabs.addTab(widget, tab_name)
        self.update_summary()

    # ================== MODIFIED: load_default_faults ==================
    def load_default_faults(self, station, phone_type=None):
        """Load default fault categories (optionally filtered by phone_type)."""
        self.category_tabs.clear()
        self.fault_inputs.clear()
        categories = self.db.get_fault_categories(station, phone_type)
        if not categories:
            widget = self.create_category_widget([(None, "No faults loaded")], "General")
            self.category_tabs.addTab(widget, "General")
            return

        for cat in categories:
            cat_id = cat['id']
            cat_name = cat['category_name']
            faults_records = self.db.get_faults_by_category(cat_id)
            fault_list = [(f['id'], f['fault_name']) for f in faults_records]
            if fault_list:
                widget = self.create_category_widget(fault_list, cat_name)
                self.category_tabs.addTab(widget, cat_name)
            else:
                widget = self.create_category_widget([(None, "No faults")], cat_name)
                self.category_tabs.addTab(widget, cat_name)
        self.update_summary()

    def on_floor_changed(self, floor):
        self.line_combo.clear()
        if floor == "2nd Floor":
            self.line_combo.addItems(["201", "202", "203", "MMI-2"])  
        elif floor == "3rd Floor":
            self.line_combo.addItems(["301", "302","MMI-2"])
        self.line_combo.setCurrentIndex(0)

    def create_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 3)
        return shadow

    def create_field_widget(self, label_text, widget, required=False):
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(layout)

        label_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setStyleSheet("color: #4a5568; font-weight: 600; font-size: 11px;")
        label_layout.addWidget(label)
        if required:
            req = QLabel("*")
            req.setStyleSheet("color: #e53e3e; font-weight: bold; font-size: 11px;")
            label_layout.addWidget(req)
        label_layout.addStretch()
        layout.addLayout(label_layout)
        layout.addWidget(widget)
        return container

    def create_styled_line_edit(self):
        line_edit = QLineEdit()
        line_edit.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                background: white;
                font-size: 12px;
                color: #2d3748;
            }
            QLineEdit:focus {
                border-color: #00b4d8;
            }
        """)
        return line_edit

    def create_styled_combo_box(self):
        combo = QComboBox()
        combo.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                background: white;
                font-size: 12px;
                color: #2d3748;
            }
            QComboBox:focus {
                border-color: #00b4d8;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background: white;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                selection-background-color: #00b4d8;
            }
        """)
        return combo

    def show_add_fault_dialog(self, category_id):
        pass  # kept for compatibility

    def update_time(self):
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))

    def update_summary(self):
        station = self.station_combo.currentText()
        if station == "Rework" and self.rework_table is not None:
            row_count = self.rework_table.rowCount()
            total_entries = 0
            total_quantity = 0
            for row in range(row_count):
                fault_item = self.rework_table.item(row, 0)
                if fault_item and fault_item.text().strip():
                    total_entries += 1
                    for col in range(1, 5):
                        item = self.rework_table.item(row, col)
                        if item:
                            text = item.text().strip()
                            if text:
                                try:
                                    total_quantity += int(text)
                                except ValueError:
                                    pass
            self.total_faults_label.setText(str(total_quantity))
            if total_entries > 0:
                summary = f"Rework entries: {total_entries} row(s) recorded.\n"
                summary += f"Total faulty units: {total_quantity} pcs\n"
                summary += "Please fill PCB, Material, Fixing, Solding columns."
            else:
                summary = "✅ No rework entries - All Pass"
            self.fault_summary_text.setText(summary)
        else:
            total_faults = 0
            fault_details = []
            for fault, spinbox in self.fault_inputs.items():
                qty = spinbox.value()
                if qty > 0:
                    total_faults += qty
                    fault_details.append(f"• {fault}: {qty} pcs")
            self.total_faults_label.setText(str(total_faults))
            if fault_details:
                summary = "Fault Details:\n" + "\n".join(fault_details[:10])
                if len(fault_details) > 10:
                    summary += f"\n... and {len(fault_details) - 10} more faults"
            else:
                summary = "✅ No faults recorded - All Pass"
            self.fault_summary_text.setText(summary)

    def load_edit_data(self):
        # --- Basic Info fields restore ---
        self.model_input.setText(self.edit_data.get('model', ''))
        self.color_input.setText(self.edit_data.get('color', ''))
        self.shipment_input.setText(self.edit_data.get('ship', ''))
        self.employee_input.setText(self.edit_data.get('employee', ''))
        self.id_input.setText(self.edit_data.get('tester_id', ''))

        line = self.edit_data.get('line', '')
        floor = self.edit_data.get('floor', '')
        if line:
            idx = self.line_combo.findText(line)
            if idx >= 0:
                self.line_combo.setCurrentIndex(idx)
        if floor:
            idx = self.floor_combo.findText(floor)
            if idx >= 0:
                self.floor_combo.setCurrentIndex(idx)

        station = self.edit_data.get('station', 'MMI Test')
        idx = self.station_combo.findText(station)
        if idx >= 0:
            self.station_combo.setCurrentIndex(idx)

        # Restore phone type
        phone_type = self.edit_data.get('phone_type', 'Feature')
        if phone_type == 'Smart':
            self.smart_radio.setChecked(True)
        else:
            self.feature_radio.setChecked(True)

        # Set date
        if 'inspection_date' in self.edit_data:
            try:
                date_obj = QDate.fromString(self.edit_data['inspection_date'], "yyyy-MM-dd")
                self.date_edit.setDate(date_obj)
            except:
                pass

        # --- FAULT TABS LOADING (Station wise) ---
        if station == "Rework":
            inspection_id = self.edit_data.get('id')
            if inspection_id:
                rework_details = self.db.get_rework_details(inspection_id)
                if self.rework_table:
                    self.rework_table.setRowCount(0)
                    if rework_details:
                        for detail in rework_details:
                            row = self.rework_table.rowCount()
                            self.rework_table.insertRow(row)
                            fault_item = QTableWidgetItem(detail.get('fault_name', ''))
                            fault_item.setFlags(fault_item.flags() & ~Qt.ItemIsEditable)
                            self.rework_table.setItem(row, 0, fault_item)
                            self.rework_table.setItem(row, 1, QTableWidgetItem(str(detail.get('pcb', ''))))
                            self.rework_table.setItem(row, 2, QTableWidgetItem(str(detail.get('material', ''))))
                            self.rework_table.setItem(row, 3, QTableWidgetItem(str(detail.get('fixing', ''))))
                            self.rework_table.setItem(row, 4, QTableWidgetItem(str(detail.get('solding', ''))))
                    else:
                        self.load_rework_faults(phone_type)
        elif station == "Final Test":
            self.load_final_test_faults(phone_type)
        elif station == "Appearance Test":
            self.load_appearance_faults(phone_type)
        elif station == "MMI Test":
            if phone_type == "Smart":
                self.load_mmi_smart_faults()
            else:
                self.load_default_faults(station, phone_type="Feature")
        else:
            # Semi Test or any other station
            self.load_default_faults(station, phone_type=phone_type)

        # ================================================================
        # 🔥 FIX: Set fault quantities for ALL stations (MMI, Appearance, Semi, etc.)
        # ================================================================
        faults = self.edit_data.get('faults', {})
        for fault_name, spinbox in self.fault_inputs.items():
            if fault_name in faults:
                spinbox.setValue(faults[fault_name])
        # ================================================================

        self.update_summary()
        self.edit_inspection_code = self.edit_data.get('inspection_code', '')
        if self.save_btn:
            self.save_btn.setText("✏️ UPDATE INSPECTION REPORT")

    def save_inspection(self):
        # --- Validations ---
        if not self.model_input.text().strip():
            CustomMessageBox.show_warning(self, "Validation", "Please enter Model.")
            return
        if not self.color_input.text().strip():
            CustomMessageBox.show_warning(self, "Validation", "Please enter Color.")
            return
        if not self.shipment_input.text().strip():
            CustomMessageBox.show_warning(self, "Validation", "Please enter Shipment.")
            return
        if not self.employee_input.text().strip():
            CustomMessageBox.show_warning(self, "Validation", "Please enter Employee Name.")
            return
        if not self.id_input.text().strip():
            CustomMessageBox.show_warning(self, "Validation", "Please enter Tester ID.")
            return

        line = self.line_combo.currentText()
        floor = self.floor_combo.currentText()
        station = self.station_combo.currentText()
        phone_type = "Feature" if self.feature_radio.isChecked() else "Smart"

        selected_date = self.date_edit.date().toPyDate()
        selected_datetime = datetime.combine(selected_date, datetime.now().time())
        date_str = selected_datetime.strftime("%d %B %Y at %H:%M:%S")

        # ---------- REWORK DATA COLLECT ----------
        if station == "Rework":
            rework_entries_raw = []
            for row in range(self.rework_table.rowCount()):
                fault = self.rework_table.item(row, 0).text().strip() if self.rework_table.item(row, 0) else ""
                pcb = self.rework_table.item(row, 1).text().strip() if self.rework_table.item(row, 1) else ""
                material = self.rework_table.item(row, 2).text().strip() if self.rework_table.item(row, 2) else ""
                fixing = self.rework_table.item(row, 3).text().strip() if self.rework_table.item(row, 3) else ""
                solding = self.rework_table.item(row, 4).text().strip() if self.rework_table.item(row, 4) else ""
                if fault:
                    rework_entries_raw.append((fault, pcb, material, fixing, solding))

            rework_dict = {}
            for fault, pcb, mat, fix, sold in rework_entries_raw:
                try:
                    pcb_qty = int(pcb) if pcb else 0
                except:
                    pcb_qty = 0
                try:
                    mat_qty = int(mat) if mat else 0
                except:
                    mat_qty = 0
                try:
                    fix_qty = int(fix) if fix else 0
                except:
                    fix_qty = 0
                try:
                    sold_qty = int(sold) if sold else 0
                except:
                    sold_qty = 0

                if fault not in rework_dict:
                    rework_dict[fault] = [0, 0, 0, 0]
                rework_dict[fault][0] += pcb_qty
                rework_dict[fault][1] += mat_qty
                rework_dict[fault][2] += fix_qty
                rework_dict[fault][3] += sold_qty

            rework_entries = []
            for fault, vals in rework_dict.items():
                total = sum(vals)
                if total > 0:
                    rework_entries.append((fault, vals[0], vals[1], vals[2], vals[3]))

            total_faults = len(rework_entries)
            status = "REWORK"
            defects_text = "\n".join([f"{f} | PCB:{p} | Mat:{m} | Fix:{fx} | Sold:{s}" for f,p,m,fx,s in rework_entries]) if rework_entries else "No rework entries"
        else:
            # ---------- OTHER STATIONS ----------
            faults_data = {}
            total_faults = 0
            for fault, spinbox in self.fault_inputs.items():
                qty = spinbox.value()
                if qty > 0:
                    faults_data[fault] = qty
                    total_faults += qty
            status = "FAIL" if total_faults > 0 else "PASS"
            defects_text = "\n".join([f"{f}: {q} pcs" for f, q in faults_data.items()]) if faults_data else "No defects"

        # Form values
        ship_value = self.shipment_input.text().strip()
        model_value = self.model_input.text().strip()

        remarks = f"Model: {model_value}, Color: {self.color_input.text()}, " \
                  f"Shipment: {ship_value}, Employee: {self.employee_input.text()}, " \
                  f"Tester ID: {self.id_input.text()}, Line: {line}, Floor: {floor}, Phone: {phone_type}"

        # ---------- SAVE ----------
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                if self.edit_mode and self.edit_inspection_code:
                    # ========== UPDATE ==========
                    cursor.execute("""
                        UPDATE inspections 
                        SET inspection_type = ?,
                            inspection_date = ?,
                            defects = ?,
                            remarks = ?,
                            rejected_quantity = ?,
                            quality_score = ?,
                            status = ?,
                            line = ?,
                            floor = ?,
                            ship = ?,
                            model = ?,
                            phone_type = ?
                        WHERE inspection_code = ?
                    """, (station, selected_datetime, defects_text[:500], remarks, total_faults,
                          100 if status == 'PASS' else 0, status, line, floor,
                          ship_value, model_value, phone_type, self.edit_inspection_code))
                    conn.commit()

                    insp = self.db.execute_query(
                        "SELECT id FROM inspections WHERE inspection_code = ?",
                        (self.edit_inspection_code,), fetch_one=True
                    )
                    inspection_id = insp['id'] if insp else None

                    if station == 'Rework' and rework_entries and inspection_id:
                        self.db.save_rework_root_cause_from_inspection(inspection_id, rework_entries)

                    CustomMessageBox.show_success(self, "Success",
                        f"✅ Inspection record updated successfully!\n\n"
                        f"📋 Code: {self.edit_inspection_code}\n"
                        f"📅 Date: {date_str}\n"
                        f"📊 Status: {status}\n"
                        f"🔧 Total Faults: {total_faults}")
                    self.data_saved.emit()
                    if self.edit_mode:
                        QTimer.singleShot(1500, lambda: self.parent().close() if self.parent() else None)

                else:
                    # ========== NEW INSERT ==========
                    inspector_id = int(self.user.get('id', 1))
                    inspection_code = f"MMI-{datetime.now().strftime('%Y%m%d%H%M%S')}-{station[:3]}"
                    cursor.execute("""
                        INSERT INTO inspections (
                            inspection_code, product_id, inspector_id, inspection_type,
                            inspection_date, quantity_checked, accepted_quantity, rejected_quantity,
                            quality_score, defects, remarks, status, line, floor, ship, model, phone_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (inspection_code, None, inspector_id, station, selected_datetime,
                          1, 1 if status == 'PASS' else 0, total_faults,
                          100 if status == 'PASS' else 0, defects_text[:500], remarks, status, line, floor,
                          ship_value, model_value, phone_type))
                    conn.commit()
                    cursor.execute("SELECT @@IDENTITY")
                    inspection_id = cursor.fetchone()[0]

                    if station == 'Rework' and rework_entries:
                        self.db.save_rework_root_cause_from_inspection(inspection_id, rework_entries)
                    else:
                        self.db.create_rework_tasks_from_inspection(inspection_id)

                    CustomMessageBox.show_success(self, "Success",
                        f"✅ Inspection saved successfully!\n\n"
                        f"📋 Code: {inspection_code}\n"
                        f"📅 Date: {date_str}\n"
                        f"📊 Status: {status}\n"
                        f"🔧 Total Faults: {total_faults}")
                    if not self.edit_mode:
                        reply = CustomMessageBox.show_question(self, "Reset Form", "🔄 Do you want to clear the form for next entry?")
                        if reply == QDialog.Accepted:
                            self.reset_form()

        except Exception as e:
            CustomMessageBox.show_error(self, "Database Error", f"❌ Failed to save!\n\nError: {str(e)}")

    def reset_form(self):
        self.model_input.clear()
        self.color_input.clear()
        self.shipment_input.clear()
        self.employee_input.clear()
        self.id_input.clear()
        self.line_combo.setCurrentIndex(0)
        self.floor_combo.setCurrentIndex(0)
        self.feature_radio.setChecked(True)
        for spinbox in self.fault_inputs.values():
            spinbox.setValue(0)
        if self.rework_table is not None:
            self.rework_table.setRowCount(0)
            self.load_rework_faults("Feature")
        self.update_summary()
        self.model_input.setFocus()