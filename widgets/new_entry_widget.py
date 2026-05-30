import sys
from datetime import datetime
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QLineEdit, QPushButton, QScrollArea,
    QGroupBox, QMessageBox, QComboBox, QTextEdit,
    QDateEdit, QTabWidget, QSpinBox, QApplication, QDialog,
    QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon
from database import Database
from custom_dialogs import CustomMessageBox


class NewEntryWidget(QWidget):
    data_saved = pyqtSignal()
    
    # Default fault list for Rework station (read-only for users)
    DEFAULT_REWORK_FAULTS = [
        "PCB", "LCD SPOT/SHADE/LINE", "LCD WHITE & BLACK", "LCD BUBBLE",
        "CAMERA BLACK/ERROR", "CAMERA BLUR", "CAMERA SPOT / SHADE", "CAMERA RIBBON",
        "VIBERTOR", "RINGER NOT WORK", "RINGER DIS", "RECEIVER NOT WORK",
        "RECEIVER DIS", "MIC", "TORCH", "KEYPAD", "DEAD", "FLASH"
    ]
    
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
        
        # Main scroll area for the whole window (no extra scroll inside fault panel)
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
        content_layout.addWidget(self.fault_panel, 2)  # give it stretch
        
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
        # Remove scroll buttons from tab bar
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
    
    # ================== REWORK PANEL WITH READ-ONLY FAULT NAMES AND NO SCROLLBAR ==================
    def create_rework_panel(self):
        """Create a table for rework entries. Fault Name column is read-only. No internal scrollbar."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        self.rework_table = QTableWidget()
        self.rework_table.setColumnCount(5)
        self.rework_table.setHorizontalHeaderLabels(["Fault Name", "PCB", "Material", "Fixing", "Solding"])
        self.rework_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rework_table.setAlternatingRowColors(True)

        # --- Explicitly disable both scrollbars ---
        self.rework_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rework_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # --- Make the table expand vertically, but never show scrollbar ---
        self.rework_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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

        # Buttons
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

        # Pre-fill with default fault list (read-only)
        for fault_name in self.DEFAULT_REWORK_FAULTS:
            row = self.rework_table.rowCount()
            self.rework_table.insertRow(row)
            fault_item = QTableWidgetItem(fault_name)
            fault_item.setFlags(fault_item.flags() & ~Qt.ItemIsEditable)
            self.rework_table.setItem(row, 0, fault_item)
            for col in range(1, 5):
                self.rework_table.setItem(row, col, QTableWidgetItem(""))

        # If no default faults (unlikely), add one editable row
        if self.rework_table.rowCount() == 0:
            self.add_rework_row()

        # --- Adjust row heights to content ---
        self.rework_table.resizeRowsToContents()

        # --- Set a reasonable minimum height so the table is never squashed ---
        row_height = self.rework_table.rowHeight(0) if self.rework_table.rowCount() > 0 else 30
        header_height = self.rework_table.horizontalHeader().height()
        min_height = header_height + self.rework_table.rowCount() * row_height + 20  # +20 for margins
        self.rework_table.setMinimumHeight(min_height)

        # Add a stretch at the end to keep buttons from floating too high
        layout.addStretch()

        return widget
        
    def add_rework_row(self):
        """Add a new row where the fault name is editable (user can type any fault)."""
        if self.rework_table is None:
            return
        row = self.rework_table.rowCount()
        self.rework_table.insertRow(row)
        # Fault name column – editable for user-added rows
        fault_item = QTableWidgetItem("")
        fault_item.setFlags(fault_item.flags() | Qt.ItemIsEditable)  # ensure editable
        self.rework_table.setItem(row, 0, fault_item)
        # Other columns
        for col in range(1, 5):
            self.rework_table.setItem(row, col, QTableWidgetItem(""))
    
    def remove_rework_row(self):
        if self.rework_table is None:
            return
        current_row = self.rework_table.currentRow()
        if current_row >= 0:
            self.rework_table.removeRow(current_row)
    # =====================================================================
    
    def create_category_widget(self, fault_list, category_id=None):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        if self.user.get('role') == 'admin' and category_id:
            admin_bar = QHBoxLayout()
            add_fault_btn = QPushButton("➕ Add New Fault")
            add_fault_btn.setStyleSheet("""
                QPushButton {
                    background: #28a745;
                    color: white;
                    border: none;
                    padding: 6px 16px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #218838;
                }
            """)
            add_fault_btn.clicked.connect(lambda: self.show_add_fault_dialog(category_id))
            admin_bar.addStretch()
            admin_bar.addWidget(add_fault_btn)
            layout.addLayout(admin_bar)
        
        cols = 2
        grid_layout = QGridLayout()
        grid_layout.setVerticalSpacing(15)
        grid_layout.setHorizontalSpacing(20)
        
        for idx, fault in enumerate(fault_list):
            fault_card = self.create_fault_card(fault, category_id)
            row = idx // cols
            col = idx % cols
            grid_layout.addWidget(fault_card, row, col)
        
        layout.addLayout(grid_layout)
        layout.addStretch()
        return widget
    
    def create_fault_card(self, fault_name, category_id=None):
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
        label.setStyleSheet("""
            color: #1e293b;
            font-weight: 600;
            font-size: 13px;
            background: transparent;
        """)
        label.setWordWrap(True)
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
    
    def on_station_changed(self, station):
        if hasattr(self, 'category_tabs'):
            self.category_tabs.clear()
            self.fault_inputs.clear()
            if station == "Rework":
                rework_panel = self.create_rework_panel()
                self.category_tabs.addTab(rework_panel, "🔄 Rework Details")
            else:
                self.load_default_faults(station)
            self.update_summary()
    
    def load_default_faults(self, station):
        if station == "Appearance Test":
            fault_list = [
                "SCREW MISSING", "SCREW LOSE", "SCREW DAMAGED", "SCREW BIT",
                "LCD DUST", "CAMERA DUST", "RINGER NET DAMAGE",
                "SIM/CD CARD HOLDER MISSING", "BT WIRE MISFIT", "TORCH OUT",
                "HOUSING DENT SCRATCH DAMAGE", "HOUSING GAP"
            ]
            widget = self.create_category_widget(fault_list)
            self.category_tabs.addTab(widget, "🔧 APPEARANCE FAULTS")
        elif station == "Semi Test":
            categories = {
                "📺 DISPLAY": ["LCD BLACK", "LCD WHITE", "LCD SHADE", "LCD SPOT", "LCD LINE", "LCD BUBBLE", "LCD BLING"],
                "🔊 AUDIO": ["RECEIVER NOT WORK", "RECEIVER DISTORTION", "RECEIVER SLOW", "RINGER NOT WORK", "RINGER DISTORTION", "RINGER SLOW", "MIC NOT WORK"],
                "📷 CAMERA": ["CAMERA BLACK/WHITE", "CAMERA ERROR", "CAMERA SHADE/SPOT/LINE", "CAMERA BLUR"],
                "💡 LED": ["TORCH NOT WORK", "ONE TORCH NOT WORK", "TORCH AUTO WORK", "FLASH NOT WORK", "FLASH AUTO WORK", "LCD DAMAGE"],
                "🔘 KEYPAD": ["KEYPAD NOT WORK", "KEYPAD WORK SOMETIME", "KEYPAD HARD", "KEYPAD AUTO WORK"],
                "⚡ POWER": ["DEAD", "AUTO OFF", "VIBRATOR NOT WORK", "VIBRATOR AUTO WORK"]
            }
            for tab_name, fault_list in categories.items():
                widget = self.create_category_widget(fault_list)
                self.category_tabs.addTab(widget, tab_name)
        elif station == "MMI Test":
            categories = {
                "📱 DISPLAY": ["LCD BLACK", "LCD WHITE", "LCD SHADE", "LCD SPOT", "LCD LINE", "LCD BUBBLE", "LCD BLING"],
                "🔊 AUDIO": ["RECEIVER NOT WORK", "RECEIVER DISTORTION", "RECEIVER SLOW", "RINGER NOT WORK", "RINGER DISTORTION", "RINGER SLOW", "MIC NOT WORK"],
                "📷 CAMERA": ["CAMERA BLACK/WHITE", "CAMERA ERROR", "CAMERA SHADE/SPOT/LINE", "CAMERA BLUR"],
                "💡 LED": ["TORCH NOT WORK", "ONE TORCH NOT WORK", "TORCH AUTO WORK", "FLASH NOT WORK", "FLASH AUTO WORK", "LCD DAMAGE"],
                "🔘 KEYPAD": ["KEYPAD NOT WORK", "KEYPAD WORK SOMETIME", "KEYPAD HARD", "KEYPAD AUTO WORK"],
                "🌐 NETWORK": ["NO NETWORK", "WEAK SIGNAL", "WIFI NOT WORKING", "BLUETOOTH ISSUE", "GPS NOT WORKING"],
                "🔋 BATTERY": ["BATTERY NOT CHARGING", "BATTERY DRAIN FAST", "BATTERY SWELLING", "OVERHEATING"],
                "📡 SENSORS": ["PROXIMITY SENSOR FAIL", "AMBIENT LIGHT SENSOR FAIL", "GYROSCOPE NOT WORK", "ACCELEROMETER ISSUE"],
                "🎮 TOUCH": ["TOUCH NOT WORKING", "TOUCH DELAY", "GHOST TOUCH", "CALIBRATION ISSUE"]
            }
            for tab_name, fault_list in categories.items():
                widget = self.create_category_widget(fault_list)
                self.category_tabs.addTab(widget, tab_name)
        elif station == "Final Test":
            categories = {
                "📦 PACKAGING": ["BOX DAMAGE", "LABEL MISSING", "BARCODE ISSUE", "MANUAL MISSING"],
                "🔋 BATTERY": ["BATTERY NOT CHARGING", "BATTERY DRAIN FAST", "BATTERY SWELLING"],
                "📡 SIGNAL": ["NO SIGNAL", "WEAK SIGNAL", "WIFI ISSUE", "BLUETOOTH ISSUE"]
            }
            for tab_name, fault_list in categories.items():
                widget = self.create_category_widget(fault_list)
                self.category_tabs.addTab(widget, tab_name)
        self.update_summary()
    
    def on_floor_changed(self, floor):
        self.line_combo.clear()
        if floor == "2nd Floor":
            self.line_combo.addItems(["201", "202", "203"])
        elif floor == "3rd Floor":
            self.line_combo.addItems(["301", "302"])
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
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Fault")
        dialog.setModal(True)
        dialog.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        label = QLabel("Enter Fault Name:")
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)
        fault_name_input = QLineEdit()
        fault_name_input.setPlaceholderText("e.g., LCD DAMAGE, BATTERY ISSUE, etc.")
        fault_name_input.setStyleSheet("padding: 10px; border: 2px solid #e2e8f0; border-radius: 8px;")
        layout.addWidget(fault_name_input)
        
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
            }
        """)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
            }
        """)
        
        def save_fault():
            fault_name = fault_name_input.text().strip()
            if fault_name:
                self.db.add_fault(category_id, fault_name)
                CustomMessageBox.show_success(self, "Success", f"✅ Fault '{fault_name}' added successfully!")
                dialog.accept()
                self.on_station_changed(self.station_combo.currentText())
            else:
                CustomMessageBox.show_warning(self, "Warning", "Please enter a fault name!")
        
        save_btn.clicked.connect(save_fault)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec_()
    
    def update_time(self):
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))
    
    def update_summary(self):
        station = self.station_combo.currentText()
        if station == "Rework" and self.rework_table is not None:
            row_count = self.rework_table.rowCount()
            total_entries = 0
            for row in range(row_count):
                fault_item = self.rework_table.item(row, 0)
                if fault_item and fault_item.text().strip():
                    total_entries += 1
            self.total_faults_label.setText(str(total_entries))
            if total_entries > 0:
                summary = f"Rework entries: {total_entries} row(s) recorded.\n"
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
        self.model_input.setText(self.edit_data.get('model', ''))
        self.color_input.setText(self.edit_data.get('color', ''))
        self.shipment_input.setText(self.edit_data.get('shipment', ''))
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
        
        if station == "Rework":
            inspection_id = self.edit_data.get('id')
            if inspection_id:
                rework_details = self.db.get_rework_details(inspection_id)
                if self.rework_table:
                    self.rework_table.setRowCount(0)
                    for detail in rework_details:
                        row = self.rework_table.rowCount()
                        self.rework_table.insertRow(row)
                        # Fault name – read-only
                        fault_item = QTableWidgetItem(detail.get('fault_name', ''))
                        fault_item.setFlags(fault_item.flags() & ~Qt.ItemIsEditable)
                        self.rework_table.setItem(row, 0, fault_item)
                        # Other columns – editable
                        self.rework_table.setItem(row, 1, QTableWidgetItem(detail.get('pcb', '')))
                        self.rework_table.setItem(row, 2, QTableWidgetItem(detail.get('material', '')))
                        self.rework_table.setItem(row, 3, QTableWidgetItem(detail.get('fixing', '')))
                        self.rework_table.setItem(row, 4, QTableWidgetItem(detail.get('solding', '')))
                    if self.rework_table.rowCount() == 0:
                        # No saved data, pre-fill with defaults (read-only)
                        for fault_name in self.DEFAULT_REWORK_FAULTS:
                            row = self.rework_table.rowCount()
                            self.rework_table.insertRow(row)
                            fault_item = QTableWidgetItem(fault_name)
                            fault_item.setFlags(fault_item.flags() & ~Qt.ItemIsEditable)
                            self.rework_table.setItem(row, 0, fault_item)
                            for col in range(1, 5):
                                self.rework_table.setItem(row, col, QTableWidgetItem(""))
        else:
            faults = self.edit_data.get('faults', {})
            for fault_name, spinbox in self.fault_inputs.items():
                if fault_name in faults:
                    spinbox.setValue(faults[fault_name])
                else:
                    spinbox.setValue(0)
        
        self.update_summary()
        self.edit_inspection_code = self.edit_data.get('inspection_code', '')
        if self.save_btn:
            self.save_btn.setText("✏️ UPDATE INSPECTION REPORT")
    
    def save_inspection(self):
        if not self.model_input.text().strip():
            CustomMessageBox.show_warning(self, "Validation Error", "❌ MODEL is required!")
            self.model_input.setFocus()
            return
        if not self.color_input.text().strip():
            CustomMessageBox.show_warning(self, "Validation Error", "❌ COLOR is required!")
            self.color_input.setFocus()
            return
        if not self.shipment_input.text().strip():
            CustomMessageBox.show_warning(self, "Validation Error", "❌ SHIPMENT is required!")
            self.shipment_input.setFocus()
            return
        if not self.employee_input.text().strip():
            CustomMessageBox.show_warning(self, "Validation Error", "❌ EMPLOYEE NAME is required!")
            self.employee_input.setFocus()
            return
        if not self.id_input.text().strip():
            CustomMessageBox.show_warning(self, "Validation Error", "❌ TESTER ID is required!")
            self.id_input.setFocus()
            return
        
        line = self.line_combo.currentText()
        floor = self.floor_combo.currentText()
        station = self.station_combo.currentText()
        
        if station == "Rework":
            rework_entries = []
            for row in range(self.rework_table.rowCount()):
                fault = self.rework_table.item(row, 0).text().strip() if self.rework_table.item(row, 0) else ""
                pcb = self.rework_table.item(row, 1).text().strip() if self.rework_table.item(row, 1) else ""
                material = self.rework_table.item(row, 2).text().strip() if self.rework_table.item(row, 2) else ""
                fixing = self.rework_table.item(row, 3).text().strip() if self.rework_table.item(row, 3) else ""
                solding = self.rework_table.item(row, 4).text().strip() if self.rework_table.item(row, 4) else ""
                if fault:
                    rework_entries.append((fault, pcb, material, fixing, solding))
            total_faults = len(rework_entries)
            status = "REWORK"
            defects_text = "\n".join([f"{f} | PCB:{p} | Mat:{m} | Fix:{fx} | Sold:{s}" for f,p,m,fx,s in rework_entries]) if rework_entries else "No rework entries"
        else:
            faults_data = {}
            total_faults = 0
            for fault, spinbox in self.fault_inputs.items():
                qty = spinbox.value()
                if qty > 0:
                    faults_data[fault] = qty
                    total_faults += qty
            status = "FAIL" if total_faults > 0 else "PASS"
            defects_text = "\n".join([f"{f}: {q} pcs" for f, q in faults_data.items()]) if faults_data else "No defects"
        
        remarks = f"Model: {self.model_input.text()}, Color: {self.color_input.text()}, " \
                  f"Shipment: {self.shipment_input.text()}, Employee: {self.employee_input.text()}, " \
                  f"Tester ID: {self.id_input.text()}, Line: {line}, Floor: {floor}"
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                if self.edit_mode and self.edit_inspection_code:
                    cursor.execute("""
                        UPDATE inspections 
                        SET inspection_type = ?,
                            defects = ?,
                            remarks = ?,
                            rejected_quantity = ?,
                            quality_score = ?,
                            status = ?
                        WHERE inspection_code = ?
                    """, (station, defects_text[:500], remarks, total_faults,
                          100 if status == 'PASS' else 0, status, self.edit_inspection_code))
                    conn.commit()
                    CustomMessageBox.show_success(self, "Success", f"✅ Inspection record updated successfully!\n\n📋 Code: {self.edit_inspection_code}\n📊 Status: {status}\n🔧 Total Faults: {total_faults}")
                    self.data_saved.emit()
                    if self.edit_mode:
                        QTimer.singleShot(1500, lambda: self.parent().close() if self.parent() else None)
                else:
                    inspector_id = int(self.user.get('id', 1))
                    inspection_code = f"MMI-{datetime.now().strftime('%Y%m%d%H%M%S')}-{station[:3]}"
                    cursor.execute("""
                        INSERT INTO inspections (
                            inspection_code, product_id, inspector_id, inspection_type,
                            inspection_date, quantity_checked, accepted_quantity, rejected_quantity,
                            quality_score, defects, remarks, status, line, floor
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (inspection_code, None, inspector_id, station, datetime.now(),
                          1, 1 if status == 'PASS' else 0, total_faults,
                          100 if status == 'PASS' else 0, defects_text[:500], remarks, status, line, floor))
                    conn.commit()
                    cursor.execute("SELECT @@IDENTITY")
                    inspection_id = cursor.fetchone()[0]
                    
                    if station == 'Rework':
                        if rework_entries:
                            self.db.save_rework_entries(inspection_id, rework_entries)
                    else:
                        if station != 'Rework':
                            self.db.create_rework_tasks_from_inspection(inspection_id)
                    
                    CustomMessageBox.show_success(self, "Success", f"✅ Inspection saved successfully!\n\n📋 Code: {inspection_code}\n📊 Status: {status}\n🔧 Total Faults: {total_faults}")
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
        # Clear fault spinboxes
        for spinbox in self.fault_inputs.values():
            spinbox.setValue(0)
        # Reset rework table
        if self.rework_table is not None:
            self.rework_table.setRowCount(0)
            for fault_name in self.DEFAULT_REWORK_FAULTS:
                row = self.rework_table.rowCount()
                self.rework_table.insertRow(row)
                fault_item = QTableWidgetItem(fault_name)
                fault_item.setFlags(fault_item.flags() & ~Qt.ItemIsEditable)
                self.rework_table.setItem(row, 0, fault_item)
                for col in range(1, 5):
                    self.rework_table.setItem(row, col, QTableWidgetItem(""))
        self.update_summary()
        self.model_input.setFocus()