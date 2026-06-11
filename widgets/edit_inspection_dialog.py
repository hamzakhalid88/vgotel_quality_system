"""
Edit Inspection Dialog – PROFESSIONAL CASCADING DROPDOWNS
==========================================================
Features:
- Professional Date Picker with calendar
- Cascading dropdowns: Date → Line → Model
- Date select → Lines load (only lines with data on that date)
- Line select → Models load (only models for that line+date)
- Modern professional design
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QFont
from database import Database
from custom_dialogs import CustomMessageBox

class EditInspectionDialog(QDialog):
    def __init__(self, db: Database, inspection_data: dict, parent=None):
        super().__init__(parent)
        self.db = db
        self.original_data = inspection_data
        self.setWindowTitle("Edit Inspection Record")
        self.setModal(True)
        self.setMinimumSize(950, 700)
        self.resize(1000, 750)

        # Apply professional styles
        self.apply_professional_styles()

        # Build professional UI
        self.build_professional_ui()

        # Load initial data
        self.load_initial_data()

        # Animate entry
        self.animate_entry()

    def apply_professional_styles(self):
        """Apply professional modern stylesheet"""
        self.setStyleSheet("""
            /* === DIALOG === */
            QDialog {
                background-color: #f8fafc;
            }

            /* === HEADER === */
            QFrame#headerFrame {
                background-color: #0f172a;
                border-radius: 16px;
                border: 2px solid #1e293b;
            }

            QLabel#headerTitle {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 5px;
            }

            QLabel#headerSubtitle {
                color: #94a3b8;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 2px;
            }

            QLabel#badge {
                background-color: #3b82f6;
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            /* === CARDS === */
            QFrame#cardFrame {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #e2e8f0;
            }

            /* === GROUP BOX === */
            QGroupBox {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
                font-size: 15px;
                color: #0f172a;
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 15px;
                padding-top: 15px;
                padding-left: 20px;
                padding-right: 20px;
                padding-bottom: 20px;
                background-color: #ffffff;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 12px;
                color: #3b82f6;
                background-color: #ffffff;
                font-size: 16px;
            }

            /* === FORM LABELS === */
            QLabel#formLabel {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: #334155;
                padding-right: 15px;
                min-width: 120px;
            }

            QLabel#infoValue {
                color: #1e40af;
                font-weight: bold;
                font-size: 13px;
                background-color: #eff6ff;
                padding: 8px 14px;
                border-radius: 8px;
                border: 1px solid #dbeafe;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            /* === DATE PICKER === */
            QDateEdit {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                padding: 12px 16px;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                background-color: #ffffff;
                color: #0f172a;
                min-height: 24px;
                min-width: 280px;
            }

            QDateEdit:focus {
                border: 2px solid #3b82f6;
                background-color: #eff6ff;
            }

            QDateEdit::drop-down {
                border: none;
                width: 40px;
                background-color: #3b82f6;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }

            QDateEdit::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid white;
                width: 0px;
                height: 0px;
            }

            QCalendarWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 12px;
            }

            QCalendarWidget QTableView {
                border: none;
                background-color: #ffffff;
                selection-background-color: #3b82f6;
                selection-color: white;
            }

            QCalendarWidget QHeaderView::section {
                background-color: #1e293b;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }

            QCalendarWidget QAbstractItemView:enabled {
                color: #0f172a;
                background-color: #ffffff;
                selection-background-color: #3b82f6;
                selection-color: white;
                border-radius: 6px;
            }

            QCalendarWidget QAbstractItemView:disabled {
                color: #cbd5e1;
            }

            /* === DROPDOWNS === */
            QComboBox {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                padding: 12px 16px;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                background-color: #ffffff;
                color: #0f172a;
                min-height: 24px;
                min-width: 280px;
            }

            QComboBox:focus {
                border: 2px solid #3b82f6;
                background-color: #eff6ff;
            }

            QComboBox::drop-down {
                border: none;
                width: 40px;
                background-color: #3b82f6;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid white;
                width: 0px;
                height: 0px;
            }

            QComboBox QAbstractItemView {
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                background-color: #ffffff;
                selection-background-color: #3b82f6;
                selection-color: white;
                padding: 8px;
                font-size: 13px;
            }

            QComboBox QAbstractItemView::item {
                padding: 10px 12px;
                border-radius: 6px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #eff6ff;
                color: #1e40af;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #3b82f6;
                color: white;
            }

            /* === LINE EDIT === */
            QLineEdit {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                padding: 12px 16px;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                background-color: #ffffff;
                color: #0f172a;
                min-height: 24px;
                min-width: 280px;
            }

            QLineEdit:focus {
                border: 2px solid #3b82f6;
                background-color: #eff6ff;
            }

            QLineEdit::placeholder {
                color: #94a3b8;
            }

            /* === TABLE === */
            QTableWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                background-color: #ffffff;
                gridline-color: #f1f5f9;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
            }

            QTableWidget::item {
                padding: 12px 10px;
                border-bottom: 1px solid #f1f5f9;
            }

            QTableWidget::item:selected {
                background-color: #dbeafe;
                color: #1e40af;
            }

            QHeaderView::section {
                background-color: #0f172a;
                color: white;
                padding: 14px 12px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-bottom: 2px solid #1e293b;
            }

            QHeaderView::section:hover {
                background-color: #1e293b;
            }

            /* === BUTTONS === */
            QPushButton {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 10px;
                border: none;
                cursor: pointer;
                min-width: 120px;
            }

            QPushButton#saveBtn {
                background-color: #10b981;
                color: white;
            }

            QPushButton#saveBtn:hover {
                background-color: #059669;
            }

            QPushButton#saveBtn:pressed {
                background-color: #047857;
                padding-top: 13px;
                padding-bottom: 11px;
            }

            QPushButton#cancelBtn {
                background-color: #ffffff;
                color: #ef4444;
                border: 2px solid #ef4444;
            }

            QPushButton#cancelBtn:hover {
                background-color: #ef4444;
                color: white;
            }

            QPushButton#cancelBtn:pressed {
                background-color: #dc2626;
                padding-top: 13px;
                padding-bottom: 11px;
            }

            /* === BANNER === */
            QFrame#bannerFrame {
                background-color: #eff6ff;
                border-radius: 10px;
                border-left: 4px solid #3b82f6;
            }

            QLabel#bannerText {
                color: #1e40af;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.5;
            }

            /* === FOOTER === */
            QFrame#footerFrame {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #e2e8f0;
            }

            QLabel#footerHint {
                color: #64748b;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            /* === SCROLLBAR === */
            QScrollBar:vertical {
                background-color: #f1f5f9;
                width: 10px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical {
                background-color: #cbd5e1;
                border-radius: 5px;
                min-height: 40px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #94a3b8;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def build_professional_ui(self):
        """Build professional UI with cascading dropdowns"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(24)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # === HEADER ===
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setFixedHeight(90)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 15, 25, 15)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(6)

        title = QLabel("✏️  Edit Inspection Record")
        title.setObjectName("headerTitle")
        title_layout.addWidget(title)

        subtitle = QLabel("Update root cause analysis with cascading filters")
        subtitle.setObjectName("headerSubtitle")
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        self.status_badge = QLabel("📝  Editing")
        self.status_badge.setObjectName("badge")
        header_layout.addWidget(self.status_badge)

        main_layout.addWidget(header)

        # === SCROLL AREA ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(24)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # === FILTERS CARD ===
        filters_card = QGroupBox("📅  Select Date & Line")
        filters_layout = QFormLayout(filters_card)
        filters_layout.setSpacing(18)
        filters_layout.setLabelAlignment(Qt.AlignRight)
        filters_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Date Picker (Professional)
        date_row = QHBoxLayout()
        date_row.setSpacing(15)

        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        self.date_picker.setMinimumWidth(320)
        self.date_picker.setDate(QDate.currentDate())

        # Style the calendar button
        self.date_picker.setStyleSheet("""
            QDateEdit::drop-down {
                background-color: #3b82f6;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                width: 40px;
            }
        """)

        # Connect date change to load lines
        self.date_picker.dateChanged.connect(self.on_date_changed)

        date_icon = QLabel("📅")
        date_icon.setStyleSheet("font-size: 20px;")
        date_row.addWidget(date_icon)
        date_row.addWidget(self.date_picker)
        date_row.addStretch()

        date_label = QLabel("Date:")
        date_label.setObjectName("formLabel")
        filters_layout.addRow(date_label, date_row)

        # Line Dropdown (Cascading from Date)
        line_row = QHBoxLayout()
        line_row.setSpacing(15)

        self.line_combo = QComboBox()
        self.line_combo.setMinimumWidth(320)
        self.line_combo.setPlaceholderText("Select a date first...")
        self.line_combo.setEnabled(False)  # Disabled until date selected

        # Connect line change to load models
        self.line_combo.currentTextChanged.connect(self.on_line_changed)

        line_icon = QLabel("🏭")
        line_icon.setStyleSheet("font-size: 20px;")
        line_row.addWidget(line_icon)
        line_row.addWidget(self.line_combo)
        line_row.addStretch()

        line_label = QLabel("Line:")
        line_label.setObjectName("formLabel")
        filters_layout.addRow(line_label, line_row)

        # Model Dropdown (Cascading from Date + Line)
        model_row = QHBoxLayout()
        model_row.setSpacing(15)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(320)
        self.model_combo.setPlaceholderText("Select a line first...")
        self.model_combo.setEnabled(False)  # Disabled until line selected

        model_icon = QLabel("🔧")
        model_icon.setStyleSheet("font-size: 20px;")
        model_row.addWidget(model_icon)
        model_row.addWidget(self.model_combo)
        model_row.addStretch()

        model_label = QLabel("Model:")
        model_label.setObjectName("formLabel")
        filters_layout.addRow(model_label, model_row)

        # Shipment
        ship_row = QHBoxLayout()
        ship_row.setSpacing(15)

        self.shipment_edit = QLineEdit()
        self.shipment_edit.setPlaceholderText("e.g., SH-2025-001")
        self.shipment_edit.setMinimumWidth(320)

        ship_icon = QLabel("📦")
        ship_icon.setStyleSheet("font-size: 20px;")
        ship_row.addWidget(ship_icon)
        ship_row.addWidget(self.shipment_edit)
        ship_row.addStretch()

        ship_label = QLabel("Shipment:")
        ship_label.setObjectName("formLabel")
        filters_layout.addRow(ship_label, ship_row)

        content_layout.addWidget(filters_card)

        # === INFO CARD ===
        info_card = QGroupBox("📊  Inspection Info")
        info_layout = QGridLayout(info_card)
        info_layout.setSpacing(15)

        self.station_label = QLabel("N/A")
        self.station_label.setObjectName("infoValue")
        self.employee_label = QLabel("N/A")
        self.employee_label.setObjectName("infoValue")
        self.date_info_label = QLabel("N/A")
        self.date_info_label.setObjectName("infoValue")

        info_layout.addWidget(QLabel("Station:"), 0, 0)
        info_layout.addWidget(self.station_label, 0, 1)
        info_layout.addWidget(QLabel("Employee:"), 0, 2)
        info_layout.addWidget(self.employee_label, 0, 3)
        info_layout.addWidget(QLabel("Date:"), 1, 0)
        info_layout.addWidget(self.date_info_label, 1, 1)

        info_layout.setColumnStretch(1, 1)
        info_layout.setColumnStretch(3, 1)

        content_layout.addWidget(info_card)

        # === FAULTS CARD ===
        faults_card = QGroupBox("🔍  Faults & Root Cause Analysis")
        faults_layout = QVBoxLayout(faults_card)
        faults_layout.setSpacing(18)

        # Banner
        banner = QFrame()
        banner.setObjectName("bannerFrame")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(18, 12, 18, 12)

        banner_icon = QLabel("💡")
        banner_icon.setStyleSheet("font-size: 18px;")
        banner_text = QLabel("Select Date → Line → Model to load specific root cause data. Each combination can have different root causes.")
        banner_text.setObjectName("bannerText")
        banner_text.setWordWrap(True)

        banner_layout.addWidget(banner_icon)
        banner_layout.addWidget(banner_text, 1)
        faults_layout.addWidget(banner)

        # Table
        self.fault_table = QTableWidget()
        self.fault_table.setColumnCount(5)
        self.fault_table.setHorizontalHeaderLabels([
            "⚠️  Fault Name", "📊  Quantity", "🔍  Root Cause", "👤  Responsible", "✅  Solution"
        ])
        self.fault_table.horizontalHeader().setStretchLastSection(True)
        self.fault_table.setAlternatingRowColors(True)
        self.fault_table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.fault_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.fault_table.setMinimumHeight(280)

        self.fault_table.setColumnWidth(0, 200)
        self.fault_table.setColumnWidth(1, 100)
        self.fault_table.setColumnWidth(2, 240)
        self.fault_table.setColumnWidth(3, 180)

        faults_layout.addWidget(self.fault_table)
        content_layout.addWidget(faults_card)
        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # === FOOTER ===
        footer = QFrame()
        footer.setObjectName("footerFrame")
        footer.setFixedHeight(80)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(25, 18, 25, 18)

        hint = QLabel("💡  Select Date first, then Line, then Model to load specific root cause data")
        hint.setObjectName("footerHint")
        footer_layout.addWidget(hint)
        footer_layout.addStretch()

        self.cancel_btn = QPushButton("❌  Cancel")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.setFixedSize(130, 46)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)

        self.save_btn = QPushButton("💾  Save Changes")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.setFixedSize(170, 46)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setDefault(True)

        footer_layout.addWidget(self.cancel_btn)
        footer_layout.addSpacing(12)
        footer_layout.addWidget(self.save_btn)

        main_layout.addWidget(footer)

        # Connect signals
        self.save_btn.clicked.connect(self.save_changes)
        self.cancel_btn.clicked.connect(self.reject)

    def animate_entry(self):
        """Smooth fade-in animation"""
        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(400)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim.start()

    def on_date_changed(self, new_date):
        """Date select hone pe lines load karo (only lines with data on that date)"""
        selected_date = new_date.toString("yyyy-MM-dd")
        print(f"Date selected: {selected_date} - Loading lines...")

        # Clear downstream dropdowns
        self.line_combo.clear()
        self.line_combo.setPlaceholderText("Loading lines...")
        self.line_combo.setEnabled(True)

        self.model_combo.clear()
        self.model_combo.setPlaceholderText("Select a line first...")
        self.model_combo.setEnabled(False)

        # Clear fault table
        self.fault_table.setRowCount(0)

        try:
            # Load lines that have data on this specific date
            lines = self.db.execute_query(
                """SELECT DISTINCT line 
                   FROM rework_root_cause 
                   WHERE record_date = ? 
                   AND line IS NOT NULL 
                   AND line != '' 
                   ORDER BY line""",
                (selected_date,),
                fetch_all=True
            )

            self.line_combo.clear()
            if lines and len(lines) > 0:
                self.line_combo.addItem("-- Select Line --")
                for l in lines:
                    line_name = l.get('line', '') if isinstance(l, dict) else (l[0] if l else '')
                    if line_name and str(line_name).strip():
                        self.line_combo.addItem(str(line_name).strip())
                self.line_combo.setPlaceholderText("Select a line...")
            else:
                self.line_combo.addItem("-- No lines found for this date --")
                self.line_combo.setEnabled(False)

        except Exception as e:
            print(f"Error loading lines for date {selected_date}: {e}")
            self.line_combo.clear()
            self.line_combo.addItem("-- Error loading lines --")
            self.line_combo.setEnabled(False)

    def on_line_changed(self, line_text):
        """Line select hone pe models load karo (only models for this line+date)"""
        if not line_text or line_text.startswith("--"):
            return

        selected_date = self.date_picker.date().toString("yyyy-MM-dd")
        print(f"Line selected: {line_text} on {selected_date} - Loading models...")

        # Clear model dropdown
        self.model_combo.clear()
        self.model_combo.setPlaceholderText("Loading models...")
        self.model_combo.setEnabled(True)

        # Clear fault table
        self.fault_table.setRowCount(0)

        try:
            # Load models that have data on this specific date + line
            models = self.db.execute_query(
                """SELECT DISTINCT model 
                   FROM rework_root_cause 
                   WHERE record_date = ? 
                   AND line = ?
                   AND model IS NOT NULL 
                   AND model != '' 
                   ORDER BY model""",
                (selected_date, line_text),
                fetch_all=True
            )

            self.model_combo.clear()
            if models and len(models) > 0:
                self.model_combo.addItem("-- Select Model --")
                for m in models:
                    model_name = m.get('model', '') if isinstance(m, dict) else (m[0] if m else '')
                    if model_name and str(model_name).strip():
                        self.model_combo.addItem(str(model_name).strip())
                self.model_combo.setPlaceholderText("Select a model...")

                # Auto-load fault data for first model if only one
                if len(models) == 1:
                    self.model_combo.setCurrentIndex(1)
                    self.load_fault_data()
            else:
                self.model_combo.addItem("-- No models found for this line+date --")
                self.model_combo.setEnabled(False)

        except Exception as e:
            print(f"Error loading models for line {line_text} on {selected_date}: {e}")
            self.model_combo.clear()
            self.model_combo.addItem("-- Error loading models --")
            self.model_combo.setEnabled(False)

    def load_fault_data(self):
        """Load fault data for selected Date + Line + Model"""
        selected_date = self.date_picker.date().toString("yyyy-MM-dd")
        selected_line = self.line_combo.currentText()
        selected_model = self.model_combo.currentText()

        if selected_line.startswith("--") or selected_model.startswith("--"):
            return

        print(f"Loading faults for: Date={selected_date}, Line={selected_line}, Model={selected_model}")

        try:
            # Load faults for this specific combination
            faults = self.db.execute_query(
                """SELECT fault_category, fault_subcategory, 
                           SUM(pcba_qty) as pcba, SUM(material_qty) as material,
                           SUM(fixing_qty) as fixing, SUM(soldering_qty) as soldering,
                           SUM(total_qty) as total
                   FROM rework_root_cause 
                   WHERE record_date = ? 
                   AND line = ?
                   AND model = ?
                   GROUP BY fault_category, fault_subcategory
                   ORDER BY total DESC""",
                (selected_date, selected_line, selected_model),
                fetch_all=True
            )

            self.fault_table.setRowCount(len(faults) if faults else 0)

            if faults:
                for row, f in enumerate(faults):
                    fault_name = f.get('fault_category', 'Unknown') if isinstance(f, dict) else str(f[0] if f else 'Unknown')
                    sub_fault = f.get('fault_subcategory', '') if isinstance(f, dict) else str(f[1] if len(f) > 1 else '')
                    total_qty = f.get('total', 0) if isinstance(f, dict) else (f[6] if len(f) > 6 else 0)

                    # Fault name
                    name_item = QTableWidgetItem(fault_name)
                    name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                    name_item.setBackground(QColor("#fef2f2"))
                    name_item.setForeground(QColor("#991b1b"))
                    font = QFont("Segoe UI", 11, QFont.Bold)
                    name_item.setFont(font)
                    self.fault_table.setItem(row, 0, name_item)

                    # Quantity
                    qty_item = QTableWidgetItem(str(total_qty))
                    qty_item.setTextAlignment(Qt.AlignCenter)
                    qty_item.setBackground(QColor("#eff6ff"))
                    qty_item.setForeground(QColor("#1e40af"))
                    font = QFont("Segoe UI", 11, QFont.Bold)
                    qty_item.setFont(font)
                    self.fault_table.setItem(row, 1, qty_item)

                    # Load root cause for this specific combination
                    try:
                        mapping = self.db.execute_query(
                            """SELECT root_cause, responsible_dept, solution_plan 
                               FROM rework_resolution_mapping 
                               WHERE fault_category = ? 
                               AND (record_date = ? OR record_date IS NULL)
                               AND (model = ? OR model IS NULL OR model = '')
                               AND (ship_no = ? OR ship_no IS NULL OR ship_no = '')
                               ORDER BY 
                                   CASE WHEN record_date = ? THEN 0 ELSE 1 END,
                                   CASE WHEN model = ? THEN 0 ELSE 1 END
                            """,
                            (fault_name, selected_date, selected_model, self.shipment_edit.text().strip(),
                             selected_date, selected_model),
                            fetch_one=True
                        )

                        if mapping:
                            self.fault_table.setItem(row, 2, QTableWidgetItem(mapping.get('root_cause', '')))
                            self.fault_table.setItem(row, 3, QTableWidgetItem(mapping.get('responsible_dept', '')))
                            self.fault_table.setItem(row, 4, QTableWidgetItem(mapping.get('solution_plan', '')))
                        else:
                            for col in range(2, 5):
                                self.fault_table.setItem(row, col, QTableWidgetItem(""))
                    except Exception as e:
                        print(f"Warning: Could not load mapping for {fault_name}: {e}")
                        for col in range(2, 5):
                            self.fault_table.setItem(row, col, QTableWidgetItem(""))

        except Exception as e:
            print(f"Error loading faults: {e}")
            CustomMessageBox.show_warning(self, "Warning", f"Could not load fault data: {str(e)}")

    def load_initial_data(self):
        """Load initial data from inspection record"""
        rec = self.original_data

        # Set date from record
        if rec.get('date'):
            try:
                date_parts = rec['date'].split('-')
                if len(date_parts) == 3:
                    self.date_picker.setDate(QDate(int(date_parts[0]), int(date_parts[1]), int(date_parts[2])))
                    # This will trigger on_date_changed to load lines
            except Exception as e:
                print(f"Warning: Could not parse date: {e}")

        # Set info labels
        self.station_label.setText(rec.get('station', 'N/A'))
        self.employee_label.setText(rec.get('employee', 'N/A'))
        self.date_info_label.setText(rec.get('date', 'N/A'))

        # Try to load shipment
        try:
            ship = self.db.execute_query(
                "SELECT TOP 1 ship_no FROM rework_root_cause WHERE remarks LIKE ?",
                (f'%{rec.get("inspection_code", "")}%',), fetch_one=True
            )
            if ship and ship.get('ship_no'):
                self.shipment_edit.setText(ship['ship_no'])
        except Exception as e:
            print(f"Warning: Could not load shipment: {e}")

    def save_changes(self):
        """Save all changes with date-specific root cause"""
        selected_date = self.date_picker.date().toString("yyyy-MM-dd")
        selected_line = self.line_combo.currentText()
        selected_model = self.model_combo.currentText()
        ship_no = self.shipment_edit.text().strip()
        saved_count = 0

        # Save root cause mappings for each fault
        for row in range(self.fault_table.rowCount()):
            fault_name = self.fault_table.item(row, 0).text()
            root_cause = self.fault_table.item(row, 2).text() if self.fault_table.item(row, 2) else ""
            responsible = self.fault_table.item(row, 3).text() if self.fault_table.item(row, 3) else ""
            solution = self.fault_table.item(row, 4).text() if self.fault_table.item(row, 4) else ""

            if root_cause or responsible or solution:
                try:
                    if hasattr(self.db, 'save_root_cause_mapping'):
                        self.db.save_root_cause_mapping(fault_name, "", {
                            'root_cause': root_cause,
                            'responsible_dept': responsible,
                            'solution': solution,
                            'model': selected_model,
                            'ship_no': ship_no,
                            'record_date': selected_date
                        })
                        saved_count += 1
                except Exception as e:
                    print(f"Warning: Could not save mapping for {fault_name}: {e}")

        # Update status badge
        self.status_badge.setText("✅  Saved")
        self.status_badge.setStyleSheet("""
            background-color: #10b981;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 12px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)

        # Show success message and close dialog
        CustomMessageBox.show_success(
            self,
            "Success",
            f"Root cause saved for:\n"
            f"Date: {selected_date}\n"
            f"Line: {selected_line}\n"
            f"Model: {selected_model}\n\n"
            f"{saved_count} mapping(s) saved."
        )
        self.accept()   # ✅ Correctly indented and called after message