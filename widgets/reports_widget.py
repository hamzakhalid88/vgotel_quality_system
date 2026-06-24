import csv, re, os, datetime
from typing import Dict, List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate, QTimer, QSizeF, QMarginsF
from PyQt5.QtGui import QColor, QFont, QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from database import Database
from custom_dialogs import CustomMessageBox
from .reports_common import normalize_model, get_variants, RootCauseDialog, FaultDetailsDialog

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class ReportsWidget(QWidget):
    # ========== FAULT CATEGORY MAPPING (for manual entries) ==========
    FAULT_CATEGORY_MAP = {
        # AUDIO
        'RINGER NOT WORK': 'AUDIO',
        'RINGER DIS': 'AUDIO',
        'RINGER': 'AUDIO',
        'RECEIVER NOT WORK': 'AUDIO',
        'RECEIVER DIS': 'AUDIO',
        'RECEIVER': 'AUDIO',
        'MIC': 'AUDIO',
        'MIC NOT WORK': 'AUDIO',
        # DISPLAY
        'LCD SPOT/SHADE/LINE': 'DISPLAY',
        'LCD WHITE & BLACK': 'DISPLAY',
        'LCD BLACK': 'DISPLAY',
        'LCD WHITE': 'DISPLAY',
        'LCD SHADE': 'DISPLAY',
        'LCD SPOT': 'DISPLAY',
        'LCD LINE': 'DISPLAY',
        'LCD BUBBLE': 'DISPLAY',
        'LCD BLING': 'DISPLAY',
        'LCD DAMAGE': 'DISPLAY',
        # CAMERA
        'CAMERA BLACK/ERROR': 'CAMERA',
        'CAMERA BLUR': 'CAMERA',
        'CAMERA SPOT / SHADE': 'CAMERA',
        'CAMERA RIBBON': 'CAMERA',
        # POWER / VIBRATOR
        'VIBERTOR': 'POWER',
        'VIBRATOR': 'POWER',
        'VIBRATOR NOT WORK': 'POWER',
        'VIBRATOR AUTO WORK': 'POWER',
        'DEAD': 'POWER',
        'AUTO OFF': 'POWER',
        # LED / TORCH
        'TORCH': 'LED',
        'TORCH NOT WORK': 'LED',
        'ONE TORCH NOT WORK': 'LED',
        'TORCH AUTO WORK': 'LED',
        'FLASH NOT WORK': 'LED',
        'FLASH AUTO WORK': 'LED',
        # KEYPAD
        'KEYPAD': 'KEYPAD',
        'KEYPAD NOT WORK': 'KEYPAD',
        'KEYPAD WORK SOMETIME': 'KEYPAD',
        'KEYPAD HARD': 'KEYPAD',
        'KEYPAD AUTO WORK': 'KEYPAD',
        # NETWORK
        'NO NETWORK': 'NETWORK',
        'WEAK SIGNAL': 'NETWORK',
        'WIFI NOT WORKING': 'NETWORK',
        'BLUETOOTH ISSUE': 'NETWORK',
        'GPS NOT WORKING': 'NETWORK',
        # SENSORS
        'PROXIMITY SENSOR FAIL': 'SENSOR',
        'AMBIENT LIGHT SENSOR FAIL': 'SENSOR',
        'GYROSCOPE NOT WORK': 'SENSOR',
        'ACCELEROMETER ISSUE': 'SENSOR',
        # BATTERY
        'BATTERY NOT CHARGING': 'BATTERY',
        'BATTERY DRAIN FAST': 'BATTERY',
        'BATTERY SWELLING': 'BATTERY',
        'OVERHEATING': 'BATTERY',
        # TOUCH
        'TOUCH NOT WORKING': 'TOUCH',
        'TOUCH DELAY': 'TOUCH',
        'GHOST TOUCH': 'TOUCH',
        'CALIBRATION ISSUE': 'TOUCH',
        # Default
        'DEFAULT': 'OTHER'
    }

    def __init__(self, db: Database, user_role: str):
        super().__init__()
        self.db = db
        self.user_role = user_role
        self.all_data = []
        self.filtered_data = []
        self.line_model_map = {}
        self.all_models = []
        self.rc_rows = []  # store current rows for editing
        self.setup_ui()
        self.ensure_tables_exist()
        self.load_inspections()
        self.load_completed_rework()
        self.load_rework_report()

    # ------------------------------------------------------------------
    # Ensure database tables exist
    # ------------------------------------------------------------------
    def ensure_tables_exist(self):
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_root_cause' AND xtype='U')
                CREATE TABLE rework_root_cause (id INT IDENTITY PRIMARY KEY, ship_no NVARCHAR(50), record_date DATE,
                line NVARCHAR(50), model NVARCHAR(100), fault_category NVARCHAR(100), fault_subcategory NVARCHAR(200),
                pcba_qty INT DEFAULT 0, material_qty INT DEFAULT 0, fixing_qty INT DEFAULT 0, soldering_qty INT DEFAULT 0,
                total_qty INT DEFAULT 0, remarks NVARCHAR(MAX), imported_at DATETIME DEFAULT GETDATE())""")
            c.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_completed' AND xtype='U')
                CREATE TABLE rework_completed (id INT IDENTITY PRIMARY KEY, line NVARCHAR(50), model NVARCHAR(100),
                fault_name NVARCHAR(200), source_station NVARCHAR(100), resolved_qty INT, resolution_date DATE,
                remarks NVARCHAR(MAX), created_at DATETIME DEFAULT GETDATE())""")
            c.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_resolution_mapping' AND xtype='U')
                CREATE TABLE rework_resolution_mapping (
                    id INT IDENTITY PRIMARY KEY,
                    fault_category NVARCHAR(100),
                    fault_subcategory NVARCHAR(200),
                    root_cause NVARCHAR(MAX),
                    responsible_dept NVARCHAR(100),
                    solution_plan NVARCHAR(MAX),
                    model NVARCHAR(100),
                    ship_no NVARCHAR(50),
                    record_date DATE,
                    is_weak_point BIT DEFAULT 0,
                    created_at DATETIME DEFAULT GETDATE(),
                    updated_at DATETIME DEFAULT GETDATE()
                )""")
            for col, dtype in [("model", "NVARCHAR(100)"), ("ship_no", "NVARCHAR(50)"),
                               ("record_date", "DATE"), ("is_weak_point", "BIT DEFAULT 0")]:
                try:
                    c.execute(f"ALTER TABLE rework_resolution_mapping ADD {col} {dtype}")
                except:
                    pass
            conn.commit()

    # ------------------------------------------------------------------
    # Main UI setup
    # ------------------------------------------------------------------
    def setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(15,15,15,15)
        main.setSpacing(10)
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                background: white;
            }
            QTabBar::tab {
                background: #f1f5f9;
                padding: 10px 25px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                color: #334155;
            }
            QTabBar::tab:selected {
                background: #0f2027;
                color: white;
            }
            QTabBar::tab:hover {
                background: #cbd5e1;
            }
        """)
        self.inspections_tab = QWidget(); self.setup_inspections_tab()
        self.rework_tab = QWidget(); self.setup_rework_tab()
        self.rework_report_tab = QWidget(); self.setup_rework_report_tab()
        self.line_summary_tab = QWidget(); self.setup_line_rework_summary_tab()
        self.monthly_compare_tab = QWidget(); self.setup_monthly_compare_tab()
        self.root_cause_tab = QWidget(); self.setup_root_cause_tab()

        self.tab_widget.addTab(self.inspections_tab, "📋 Inspections")
        self.tab_widget.addTab(self.rework_tab, "✅ Rework Complete")
        self.tab_widget.addTab(self.rework_report_tab, "📊 Rework Report")
        self.tab_widget.addTab(self.line_summary_tab, "🔧 Rework Summary")
        self.tab_widget.addTab(self.monthly_compare_tab, "📅 Monthly Compare")
        self.tab_widget.addTab(self.root_cause_tab, "🔍 Root Cause")
        main.addWidget(self.tab_widget)

    # --------------------------- UI Helpers ---------------------------
    def _header_frame(self, title, extra_widget=None):
        frame = QFrame()
        frame.setFixedHeight(50)
        frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f2027, stop:0.5 #203a43, stop:1 #2c5364);
            border-radius: 10px;
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20,0,20,0)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: white;")
        layout.addWidget(lbl)
        layout.addStretch()
        if extra_widget:
            extra_widget.setStyleSheet("color: #00b4d8; font-size: 12px; font-weight: bold; background: rgba(0,0,0,0.2); padding: 5px 12px; border-radius: 20px;")
            layout.addWidget(extra_widget)
        return frame

    def _simple_filter_frame(self, widgets):
        frame = QFrame()
        frame.setFixedHeight(65)
        frame.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #e0e0e0;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15,8,15,8)
        layout.setSpacing(10)
        for w in widgets:
            if isinstance(w, QLabel):
                w.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 12px;")
            layout.addWidget(w)
        layout.addStretch()
        return frame

    def _btn(self, text, color, slot):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {self._darken_color(color)};
            }}
        """)
        btn.clicked.connect(slot)
        return btn

    def _darken_color(self, color):
        color_map = {
            "#00b4d8": "#0096c7",
            "#28a745": "#218838",
            "#ffc107": "#e0a800",
            "#0f2027": "#1a2a3a",
            "#475569": "#334155",
            "#1E3A5F": "#152b44",
            "#6B7280": "#4b5563",
            "#3B82F6": "#2563EB",
            "#DC2626": "#B91C1C",
            "#1E3A8A": "#1e3a6e",
        }
        return color_map.get(color, color)

    # ------------------------------------------------------------------
    # Inspections Tab
    # ------------------------------------------------------------------
    def setup_inspections_tab(self):
        layout = QVBoxLayout(self.inspections_tab)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(10)
        self.last_updated = QLabel("")
        self.last_updated.setStyleSheet("color: #00b4d8; font-size: 10px;")
        self.records_count = QLabel("")
        self.records_count.setStyleSheet("color: #00b4d8; font-size: 11px; font-weight: bold;")
        layout.addWidget(self._header_frame("📊 INSPECTION REPORTS", self._header_right_widget()))

        self.date_from = QDateEdit(QDate(2000,1,1)); self.date_from.setCalendarPopup(True)
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        self.station_filter = QComboBox()
        self.station_filter.addItems(["All","Semi Test","MMI Test","Appearance Test","Final Test"])
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Model, Employee, ID, Fault, Line, Floor...")
        gen_btn = self._btn("🔄 Refresh", "#00b4d8", self.generate_inspection_report)
        export_btn = self._btn("📥 CSV", "#28a745", self.export_csv)

        # ========== DELETE BUTTON FOR INSPECTIONS ==========
        delete_inspection_btn = self._btn("🗑 Delete", "#DC2626", self.delete_selected_inspection)
        delete_inspection_btn.setToolTip("Permanently delete selected inspection and all linked data")

        widgets = [
            QLabel("📅 From:"), self.date_from,
            QLabel("To:"), self.date_to,
            QFrame(styleSheet="background: #ddd; max-width: 1px;"),
            QLabel("🏭 Station:"), self.station_filter,
            QFrame(styleSheet="background: #ddd; max-width: 1px;"),
            QLabel("🔎 Search:"), self.search_input, gen_btn, export_btn, delete_inspection_btn
        ]
        if PANDAS_AVAILABLE:
            excel_btn = self._btn("📊 Excel", "#ffc107", self.export_excel)
            widgets.append(excel_btn)
        layout.addWidget(self._simple_filter_frame(widgets))

        self.report_table = QTableWidget()
        self.report_table.setColumnCount(9)
        self.report_table.setHorizontalHeaderLabels(["Date","Time","Station","Model","Employee Name","Employee ID","Line","Floor","Faults"])
        self.report_table.setAlternatingRowColors(True)
        self.report_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                gridline-color: #f1f5f9;
            }
            QHeaderView::section {
                background: #1e293b;
                color: white;
                padding: 12px;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-bottom: 2px solid #334155;
            }
            QTableWidget::item {
                padding: 8px;
                font-size: 12px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background: #eef2ff;
                color: #1e3c72;
            }
        """)
        self.report_table.setSortingEnabled(True)
        self.report_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.report_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.report_table.horizontalHeader().setStretchLastSection(True)
        widths = [90,70,110,150,130,90,70,80,0]
        for i,w in enumerate(widths):
            if w>0: self.report_table.setColumnWidth(i,w)
        layout.addWidget(self.report_table)
        self.report_table.itemDoubleClicked.connect(self.on_row_double_clicked)

        footer = QFrame()
        footer.setFixedHeight(30)
        foot_layout = QHBoxLayout(footer)
        foot_layout.setContentsMargins(5,0,5,0)
        self.footer_label = QLabel("")
        self.footer_label.setStyleSheet("color: #666; font-size: 10px;")
        foot_layout.addWidget(self.footer_label)
        foot_layout.addStretch()
        self.quick_stats = QLabel("")
        self.quick_stats.setStyleSheet("color: #00b4d8; font-size: 10px; font-weight: bold;")
        foot_layout.addWidget(self.quick_stats)
        layout.addWidget(footer)

        self.date_from.dateChanged.connect(self.generate_inspection_report)
        self.date_to.dateChanged.connect(self.generate_inspection_report)
        self.station_filter.currentTextChanged.connect(self.generate_inspection_report)
        self.search_input.textChanged.connect(self.generate_inspection_report)

    def _header_right_widget(self):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0,0,0,0)
        h.addWidget(self.last_updated)
        h.addSpacing(15)
        h.addWidget(self.records_count)
        return w

    # ------------------------------------------------------------------
    # Rework Root Cause Tab (Tab2)
    # ------------------------------------------------------------------
    def setup_rework_tab(self):
        layout = QVBoxLayout(self.rework_tab)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(10)
        self.rework_total_label = QLabel("")
        self.rework_total_label.setStyleSheet("color: #00b4d8; font-weight: bold;")
        layout.addWidget(self._header_frame("✅ REWORK ROOT CAUSE (Fixed Faults)", self.rework_total_label))

        filter_frame = QFrame()
        filter_frame.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #e0e0e0;")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15,5,15,5)
        self.rework_line_filter = QLineEdit(); self.rework_line_filter.setPlaceholderText("Line")
        self.rework_model_filter = QLineEdit(); self.rework_model_filter.setPlaceholderText("Model")
        refresh = self._btn("🔄 Refresh", "#00b4d8", self.load_completed_rework)

        # ========== DELETE BUTTON FOR REWORK RECORDS ==========
        delete_btn = self._btn("🗑 Delete Selected", "#DC2626", self.delete_selected_rework_record)

        filter_layout.addWidget(QLabel("Line:")); filter_layout.addWidget(self.rework_line_filter)
        filter_layout.addWidget(QLabel("Model:")); filter_layout.addWidget(self.rework_model_filter)
        filter_layout.addStretch()
        filter_layout.addWidget(refresh)
        filter_layout.addWidget(delete_btn)
        layout.addWidget(filter_frame)

        self.rework_table = QTableWidget()
        self.rework_table.setAlternatingRowColors(True)
        self.rework_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
            QHeaderView::section {
                background: #1e293b;
                color: white;
                padding: 10px;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.rework_table)

        btn_row = QHBoxLayout()
        csv_btn = self._btn("📥 CSV", "#28a745", self.export_rework_csv)
        btn_row.addWidget(csv_btn)
        if PANDAS_AVAILABLE:
            excel_btn = self._btn("📊 Excel", "#ffc107", self.export_rework_excel)
            btn_row.addWidget(excel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.rework_line_filter.textChanged.connect(self.load_completed_rework)
        self.rework_model_filter.textChanged.connect(self.load_completed_rework)

    # ------------------------------------------------------------------
    # Rework Aggregate Report Tab (Tab3)
    # ------------------------------------------------------------------
    def setup_rework_report_tab(self):
        layout = QVBoxLayout(self.rework_report_tab)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(10)
        self.report_total_label = QLabel("")
        self.report_total_label.setStyleSheet("color: #00e5ff; font-weight: bold; background: rgba(0,0,0,0.3); padding: 5px 12px; border-radius: 20px;")
        layout.addWidget(self._header_frame("📊 REWORK AGGREGATE REPORT", self.report_total_label))

        panel = QFrame()
        panel.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e2e8f0;")
        grid = QGridLayout(panel)
        grid.setContentsMargins(15,10,15,10)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(8)

        self.report_date_from = QDateEdit(QDate.currentDate().addMonths(-1)); self.report_date_from.setCalendarPopup(True)
        self.report_date_to = QDateEdit(QDate.currentDate()); self.report_date_to.setCalendarPopup(True)
        self.report_line_filter = QComboBox(); self.report_line_filter.addItem("All")
        self.report_model_filter = QComboBox(); self.report_model_filter.addItem("All")
        self.report_fault_filter = QComboBox(); self.report_fault_filter.addItem("All")
        refresh_btn = self._btn("🔄 Generate Report", "#0f2027", self.load_rework_report)
        print_btn = self._btn("🖨️ Print", "#475569", self.print_rework_report)
        csv_btn = self._btn("📥 CSV", "#28a745", self.export_rework_report_csv)

        grid.addWidget(QLabel("📅 From:"),0,0); grid.addWidget(self.report_date_from,0,1)
        grid.addWidget(QLabel("To:"),0,2); grid.addWidget(self.report_date_to,0,3)
        grid.addWidget(QLabel("Line:"),1,0); grid.addWidget(self.report_line_filter,1,1)
        grid.addWidget(QLabel("Model:"),1,2); grid.addWidget(self.report_model_filter,1,3)
        grid.addWidget(QLabel("Fault Category:"),1,4); grid.addWidget(self.report_fault_filter,1,5)
        grid.addWidget(refresh_btn,0,4,1,2)
        grid.addWidget(print_btn,0,6,1,1)
        grid.addWidget(csv_btn,2,0,1,1)
        if PANDAS_AVAILABLE:
            excel_btn = self._btn("📊 Excel", "#ffc107", self.export_rework_report_excel)
            grid.addWidget(excel_btn,2,1,1,1)

        layout.addWidget(panel)

        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;")
        self.summary_card.setVisible(False)
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-size: 12px; color: #334155; font-weight: 500;")
        card_layout = QHBoxLayout(self.summary_card)
        card_layout.setContentsMargins(15,10,15,10)
        card_layout.addWidget(self.summary_label)
        card_layout.addStretch()
        layout.addWidget(self.summary_card)

        self.report_scroll = QScrollArea()
        self.report_scroll.setWidgetResizable(True)
        self.report_scroll.setStyleSheet("QScrollArea { border: none; background: #f1f5f9; border-radius: 12px; }")
        self.report_container = QWidget()
        self.report_layout = QVBoxLayout(self.report_container)
        self.report_layout.setContentsMargins(15,15,15,15)
        self.report_layout.setSpacing(20)
        self.report_scroll.setWidget(self.report_container)
        layout.addWidget(self.report_scroll)

        self.load_line_model_options()
        self.load_fault_categories()
        self.report_line_filter.currentTextChanged.connect(self.on_line_changed)

    # ------------------------------------------------------------------
    # Line Rework Summary Tab (Tab4) - Edit button removed
    # ------------------------------------------------------------------
    def setup_line_rework_summary_tab(self):
        layout = QVBoxLayout(self.line_summary_tab)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(10)
        layout.addWidget(self._header_frame("🔧 LINE REWORK SUMMARY (Full Breakdown)", None))

        panel = QFrame()
        panel.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #e0e0e0;")
        grid = QGridLayout(panel)
        grid.setContentsMargins(15,10,15,10)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(8)

        self.summary_line_combo = QComboBox(); self.summary_line_combo.addItem("All Lines")
        self.summary_model_combo = QComboBox(); self.summary_model_combo.setEditable(True)
        self.summary_date_from = QDateEdit(QDate.currentDate().addMonths(-1)); self.summary_date_from.setCalendarPopup(True)
        self.summary_date_to = QDateEdit(QDate.currentDate()); self.summary_date_to.setCalendarPopup(True)
        self.summary_cat_combo = QComboBox(); self.summary_cat_combo.addItem("All Categories")
        self.summary_sub_combo = QComboBox(); self.summary_sub_combo.setEditable(True)
        gen_btn = self._btn("🔄 Generate", "#0f2027", self.generate_line_rework_summary)
        html_btn = self._btn("📄 Export HTML", "#6B7280", self.export_line_summary_html)
        print_btn = self._btn("🖨️ Print", "#1E3A5F", self.print_line_summary)

        grid.addWidget(QLabel("Line:"),0,0); grid.addWidget(self.summary_line_combo,0,1)
        grid.addWidget(QLabel("Model:"),0,2); grid.addWidget(self.summary_model_combo,0,3)
        grid.addWidget(QLabel("From:"),0,4); grid.addWidget(self.summary_date_from,0,5)
        grid.addWidget(QLabel("To:"),0,6); grid.addWidget(self.summary_date_to,0,7)
        grid.addWidget(QLabel("Fault Category:"),1,0); grid.addWidget(self.summary_cat_combo,1,1)
        grid.addWidget(QLabel("Sub-Fault:"),1,2); grid.addWidget(self.summary_sub_combo,1,3)
        grid.addWidget(gen_btn,2,0,1,2)
        grid.addWidget(html_btn,2,2,1,2)
        grid.addWidget(print_btn,2,4,1,2)
        grid.setColumnStretch(7,1)
        layout.addWidget(panel)

        self.summary_output = QTextEdit()
        self.summary_output.setReadOnly(True)
        self.summary_output.document().setDocumentMargin(0)
        self.summary_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.summary_output.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                font-family: 'Segoe UI';
                font-size: 12px;
                padding: 0;
            }
        """)
        layout.addWidget(self.summary_output, stretch=1)

        self.populate_line_combo()
        self.populate_fault_categories_summary()
        self.populate_sub_faults_all()
        self.summary_line_combo.currentTextChanged.connect(self.on_summary_line_changed)
        self.summary_cat_combo.currentTextChanged.connect(self.on_summary_cat_changed)

    # ------------------------------------------------------------------
    # Monthly Compare Tab
    # ------------------------------------------------------------------
    def setup_monthly_compare_tab(self):
        layout = QVBoxLayout(self.monthly_compare_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header_frame = QFrame()
        header_frame.setFixedHeight(50)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1E3A8A, stop:1 #3B82F6);
                border-radius: 10px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 0, 20, 0)
        title_label = QLabel("📊 MONTHLY COMPARISON")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: white;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addWidget(header_frame)

        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 12px;
                border: 1px solid #E2E8F0;
            }
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 10, 15, 10)
        filter_layout.setSpacing(15)

        line_lbl = QLabel("Line:")
        line_lbl.setStyleSheet("font-weight: 600; color: #1E293B;")
        self.compare_line_combo = QComboBox()
        self.compare_line_combo.addItem("All Lines")
        self.populate_compare_line_combo()
        self.compare_line_combo.setStyleSheet("padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 8px; background: white; min-width: 120px;")

        model_lbl = QLabel("Model:")
        model_lbl.setStyleSheet("font-weight: 600; color: #1E293B;")
        self.compare_model_combo = QComboBox()
        self.compare_model_combo.addItem("All Models")
        self.compare_model_combo.setStyleSheet("padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 8px; background: white; min-width: 120px;")

        metric_lbl = QLabel("Metric:")
        metric_lbl.setStyleSheet("font-weight: 600; color: #1E293B;")
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["Total", "PCBA", "Material", "Fixing", "Soldering"])
        self.metric_combo.setStyleSheet("padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 8px; background: white; min-width: 100px;")

        lbl1 = QLabel("Month 1:")
        lbl1.setStyleSheet("font-weight: 600; color: #1E293B;")
        self.month1_start = QDateEdit(QDate.currentDate().addMonths(-1))
        self.month1_start.setCalendarPopup(True)
        self.month1_start.setDate(QDate.currentDate().addMonths(-1))
        self.month1_start.setDisplayFormat("MMMM yyyy")
        self.month1_start.setStyleSheet("padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 8px; background: white; min-width: 130px;")
        self.month1_end = QDateEdit()
        self.month1_end.setVisible(False)

        lbl2 = QLabel("Month 2:")
        lbl2.setStyleSheet("font-weight: 600; color: #1E293B;")
        self.month2_start = QDateEdit(QDate.currentDate())
        self.month2_start.setCalendarPopup(True)
        self.month2_start.setDate(QDate.currentDate())
        self.month2_start.setDisplayFormat("MMMM yyyy")
        self.month2_start.setStyleSheet("padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 8px; background: white; min-width: 130px;")
        self.month2_end = QDateEdit()
        self.month2_end.setVisible(False)

        btn_compare = QPushButton("🔄 Compare")
        btn_compare.setCursor(Qt.PointingHandCursor)
        btn_compare.setStyleSheet("background: #3B82F6; color: white; border: none; border-radius: 8px; padding: 6px 16px; font-weight: bold; font-size: 12px;")
        btn_compare.clicked.connect(self.generate_monthly_comparison)

        btn_pdf = QPushButton("📄 PDF")
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.setStyleSheet("background: #DC2626; color: white; border: none; border-radius: 8px; padding: 6px 16px; font-weight: bold; font-size: 12px;")
        btn_pdf.clicked.connect(self.export_monthly_compare_pdf)

        filter_layout.addWidget(line_lbl)
        filter_layout.addWidget(self.compare_line_combo)
        filter_layout.addWidget(model_lbl)
        filter_layout.addWidget(self.compare_model_combo)
        filter_layout.addWidget(metric_lbl)
        filter_layout.addWidget(self.metric_combo)
        filter_layout.addWidget(lbl1)
        filter_layout.addWidget(self.month1_start)
        filter_layout.addWidget(lbl2)
        filter_layout.addWidget(self.month2_start)
        filter_layout.addStretch()
        filter_layout.addWidget(btn_compare)
        filter_layout.addWidget(btn_pdf)

        layout.addWidget(filter_frame)

        self.metrics_frame = QFrame()
        self.metrics_frame.setStyleSheet("background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;")
        metrics_layout = QHBoxLayout(self.metrics_frame)
        metrics_layout.setContentsMargins(15, 10, 15, 10)
        metrics_layout.setSpacing(20)

        self.m1_metric_label = QLabel("Month 1: 0")
        self.m1_metric_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b;")
        self.m2_metric_label = QLabel("Month 2: 0")
        self.m2_metric_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b;")
        self.diff_metric_label = QLabel("Difference: 0")
        self.diff_metric_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.pct_metric_label = QLabel("Change: 0%")
        self.pct_metric_label.setStyleSheet("font-size: 14px; font-weight: bold;")

        metrics_layout.addWidget(self.m1_metric_label)
        metrics_layout.addWidget(self.m2_metric_label)
        metrics_layout.addWidget(self.diff_metric_label)
        metrics_layout.addWidget(self.pct_metric_label)
        metrics_layout.addStretch()
        layout.addWidget(self.metrics_frame)

        self.compare_table = QTableWidget()
        self.compare_table.setAlternatingRowColors(True)
        self.compare_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                gridline-color: #E2E8F0;
            }
            QHeaderView::section {
                background: #1E3A8A;
                color: white;
                padding: 8px;
                font-weight: bold;
                font-size: 11px;
                border: none;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QTableWidget::item:selected {
                background: #DBEAFE;
                color: #1E3A8A;
            }
        """)
        self.compare_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.compare_table.setSortingEnabled(False)
        layout.addWidget(self.compare_table)

        self._update_month1_end()
        self._update_month2_end()

        self.compare_line_combo.currentTextChanged.connect(self.populate_compare_model_combo)
        self.compare_model_combo.currentTextChanged.connect(self.on_compare_model_changed)
        self.metric_combo.currentTextChanged.connect(self.generate_monthly_comparison)
        self.month1_start.dateChanged.connect(self._update_month1_end)
        self.month2_start.dateChanged.connect(self._update_month2_end)

    def _update_month1_end(self):
        start = self.month1_start.date()
        last_day = start.addDays(start.daysInMonth() - 1)
        self.month1_end.setDate(last_day)
        if self.compare_model_combo.currentText() == "All Models":
            QTimer.singleShot(50, self.generate_monthly_comparison)

    def _update_month2_end(self):
        start = self.month2_start.date()
        last_day = start.addDays(start.daysInMonth() - 1)
        self.month2_end.setDate(last_day)
        if self.compare_model_combo.currentText() == "All Models":
            QTimer.singleShot(50, self.generate_monthly_comparison)

    def populate_compare_line_combo(self):
        rows = self.db.execute_query(
            "SELECT DISTINCT line FROM rework_root_cause WHERE line IS NOT NULL AND line != '' ORDER BY line",
            fetch_all=True
        )
        self.compare_line_combo.blockSignals(True)
        self.compare_line_combo.clear()
        self.compare_line_combo.addItem("All Lines")
        for r in rows:
            self.compare_line_combo.addItem(r['line'])
        self.compare_line_combo.blockSignals(False)

    def populate_compare_model_combo(self, line):
        self.compare_model_combo.blockSignals(True)
        self.compare_model_combo.clear()
        self.compare_model_combo.addItem("All Models")

        if line == "All Lines" or not line:
            rows = self.db.execute_query(
                "SELECT DISTINCT model FROM rework_root_cause WHERE model IS NOT NULL AND model != '' ORDER BY model",
                fetch_all=True
            )
        else:
            rows = self.db.execute_query(
                "SELECT DISTINCT model FROM rework_root_cause WHERE [line] = ? AND model IS NOT NULL AND model != '' ORDER BY model",
                (line,),
                fetch_all=True
            )

        seen_canonical = set()
        for r in rows:
            raw_model = r['model']
            canonical = normalize_model(raw_model)
            if canonical not in seen_canonical:
                seen_canonical.add(canonical)
                self.compare_model_combo.addItem(canonical)

        self.compare_model_combo.blockSignals(False)
        QTimer.singleShot(50, self.generate_monthly_comparison)

    def on_compare_model_changed(self, model):
        QTimer.singleShot(50, self.generate_monthly_comparison)

    # ------------------------------------------------------------------
    # Monthly Comparison – Core logic
    # ------------------------------------------------------------------
    def generate_monthly_comparison(self):
        start1_date = self.month1_start.date()
        end1_date = self.month1_end.date()
        start1 = start1_date.toString("yyyy-MM-dd")
        end1 = end1_date.toString("yyyy-MM-dd")

        start2_date = self.month2_start.date()
        end2_date = self.month2_end.date()
        start2 = start2_date.toString("yyyy-MM-dd")
        end2 = end2_date.toString("yyyy-MM-dd")

        selected_line = self.compare_line_combo.currentText()
        selected_model = self.compare_model_combo.currentText()
        selected_metric = self.metric_combo.currentText().lower()

        metric_column = {
            "total": "total_qty",
            "pcba": "pcba_qty",
            "material": "material_qty",
            "fixing": "fixing_qty",
            "soldering": "soldering_qty"
        }.get(selected_metric, "total_qty")

        def safe_int(val):
            return val if isinstance(val, (int, float)) and val is not None else 0

        base_filters = []
        base_params1 = [start1, end1]
        base_params2 = [start2, end2]

        if selected_line != "All Lines" and selected_line:
            base_filters.append("[line] = ?")
            base_params1.append(selected_line)
            base_params2.append(selected_line)

        where_clause = " AND " + " AND ".join(base_filters) if base_filters else ""

        if selected_model != "All Models" and selected_model:
            variants = get_variants(selected_model)
            placeholders = ','.join(['?'] * len(variants))

            if selected_line == "All Lines" or not selected_line:
                group_fields = "[line], ship_no"
                select_fields = "[line], ISNULL(ship_no, 'NO_LOT') as ship_no"
            else:
                group_fields = "ship_no"
                select_fields = "ISNULL(ship_no, 'NO_LOT') as ship_no"

            query1 = f"""
                SELECT
                    {select_fields},
                    SUM({metric_column}) as value
                FROM rework_root_cause
                WHERE record_date BETWEEN ? AND ? {where_clause} AND model IN ({placeholders})
                GROUP BY {group_fields}
            """
            params1 = base_params1 + variants
            rows1 = self.db.execute_query(query1, tuple(params1), fetch_all=True)

            query2 = f"""
                SELECT
                    {select_fields},
                    SUM({metric_column}) as value
                FROM rework_root_cause
                WHERE record_date BETWEEN ? AND ? {where_clause} AND model IN ({placeholders})
                GROUP BY {group_fields}
            """
            params2 = base_params2 + variants
            rows2 = self.db.execute_query(query2, tuple(params2), fetch_all=True)

            month1_data = {}
            for r in rows1:
                if selected_line == "All Lines" or not selected_line:
                    key = (r['line'], r['ship_no'])
                else:
                    key = r['ship_no']
                month1_data[key] = {
                    'line': r['line'] if selected_line == "All Lines" else selected_line,
                    'ship': r['ship_no'],
                    'value': r['value'] or 0,
                }
            month2_data = {}
            for r in rows2:
                if selected_line == "All Lines" or not selected_line:
                    key = (r['line'], r['ship_no'])
                else:
                    key = r['ship_no']
                month2_data[key] = {
                    'line': r['line'] if selected_line == "All Lines" else selected_line,
                    'ship': r['ship_no'],
                    'value': r['value'] or 0,
                }

            all_keys = set(month1_data.keys()) | set(month2_data.keys())
            if not all_keys:
                self.compare_table.clearContents()
                self.compare_table.setRowCount(0)
                self.compare_table.setVisible(False)
                self._update_metrics(0, 0)
                QMessageBox.information(self, "Info", f"No {selected_metric} data found for model {selected_model} in the selected months.")
                return

            month1_label = self.month1_start.date().toString("MMM yyyy")
            month2_label = self.month2_start.date().toString("MMM yyyy")
            metric_label = selected_metric.capitalize()

            if selected_line == "All Lines" or not selected_line:
                headers = ["Line", "Lot No.", f"{month1_label} {metric_label}", f"{month2_label} {metric_label}", "Difference", "% Change"]
                self.compare_table.setColumnCount(6)
            else:
                headers = ["Lot No.", f"{month1_label} {metric_label}", f"{month2_label} {metric_label}", "Difference", "% Change"]
                self.compare_table.setColumnCount(5)
            self.compare_table.setHorizontalHeaderLabels(headers)
            self.compare_table.clearContents()
            self.compare_table.setRowCount(len(all_keys) + 1)

            grand_m1 = 0
            grand_m2 = 0
            row = 0
            for key in sorted(all_keys):
                m1 = month1_data.get(key, {}).get('value', 0)
                m2 = month2_data.get(key, {}).get('value', 0)
                diff = m2 - m1
                pct_change = (diff / m1 * 100) if m1 != 0 else (100 if m2 > 0 else 0)

                if selected_line == "All Lines" or not selected_line:
                    line_val = month1_data.get(key, {}).get('line') or month2_data.get(key, {}).get('line') or ''
                    ship_val = month1_data.get(key, {}).get('ship') or month2_data.get(key, {}).get('ship') or ''
                    self.compare_table.setItem(row, 0, QTableWidgetItem(line_val))
                    self.compare_table.setItem(row, 1, QTableWidgetItem(ship_val if ship_val != 'NO_LOT' else ''))
                    self.compare_table.setItem(row, 2, QTableWidgetItem(f"{m1:,}"))
                    self.compare_table.setItem(row, 3, QTableWidgetItem(f"{m2:,}"))
                    self.compare_table.setItem(row, 4, QTableWidgetItem(f"{diff:+,}"))
                    pct_item = QTableWidgetItem(f"{pct_change:+.1f}%")
                    if diff > 0:
                        pct_item.setForeground(QColor("#15803d"))
                    elif diff < 0:
                        pct_item.setForeground(QColor("#b91c1c"))
                    self.compare_table.setItem(row, 5, pct_item)
                else:
                    ship_val = key if key != 'NO_LOT' else ''
                    self.compare_table.setItem(row, 0, QTableWidgetItem(ship_val))
                    self.compare_table.setItem(row, 1, QTableWidgetItem(f"{m1:,}"))
                    self.compare_table.setItem(row, 2, QTableWidgetItem(f"{m2:,}"))
                    self.compare_table.setItem(row, 3, QTableWidgetItem(f"{diff:+,}"))
                    pct_item = QTableWidgetItem(f"{pct_change:+.1f}%")
                    if diff > 0:
                        pct_item.setForeground(QColor("#15803d"))
                    elif diff < 0:
                        pct_item.setForeground(QColor("#b91c1c"))
                    self.compare_table.setItem(row, 4, pct_item)

                grand_m1 += m1
                grand_m2 += m2
                row += 1

            grand_diff = grand_m2 - grand_m1
            grand_pct = (grand_diff / grand_m1 * 100) if grand_m1 != 0 else (100 if grand_m2 > 0 else 0)

            if selected_line == "All Lines" or not selected_line:
                self.compare_table.setItem(row, 0, QTableWidgetItem("TOTAL"))
                self.compare_table.setItem(row, 1, QTableWidgetItem(""))
                self.compare_table.setItem(row, 2, QTableWidgetItem(f"{grand_m1:,}"))
                self.compare_table.setItem(row, 3, QTableWidgetItem(f"{grand_m2:,}"))
                self.compare_table.setItem(row, 4, QTableWidgetItem(f"{grand_diff:+,}"))
                pct_total = QTableWidgetItem(f"{grand_pct:+.1f}%")
            else:
                self.compare_table.setItem(row, 0, QTableWidgetItem("TOTAL"))
                self.compare_table.setItem(row, 1, QTableWidgetItem(f"{grand_m1:,}"))
                self.compare_table.setItem(row, 2, QTableWidgetItem(f"{grand_m2:,}"))
                self.compare_table.setItem(row, 3, QTableWidgetItem(f"{grand_diff:+,}"))
                pct_total = QTableWidgetItem(f"{grand_pct:+.1f}%")
            if grand_diff > 0:
                pct_total.setForeground(QColor("#15803d"))
            elif grand_diff < 0:
                pct_total.setForeground(QColor("#b91c1c"))
            if selected_line == "All Lines" or not selected_line:
                self.compare_table.setItem(row, 5, pct_total)
            else:
                self.compare_table.setItem(row, 4, pct_total)

            self.compare_table.resizeColumnsToContents()
            self.compare_table.setVisible(True)
            self._update_metrics(grand_m1, grand_m2)
            return

        # If no model filter, aggregate by line+model
        query_pairs = f"""
            SELECT DISTINCT line, model FROM (
                SELECT line, model FROM rework_root_cause
                WHERE record_date BETWEEN ? AND ? {where_clause}
                UNION
                SELECT line, model FROM rework_root_cause
                WHERE record_date BETWEEN ? AND ? {where_clause}
            ) AS combined
            WHERE model IS NOT NULL AND model != ''
            AND line IS NOT NULL AND line != ''
        """
        params_pairs = base_params1 + base_params2
        rows_pairs = self.db.execute_query(query_pairs, tuple(params_pairs), fetch_all=True)

        if not rows_pairs:
            self.compare_table.clearContents()
            self.compare_table.setRowCount(0)
            self.compare_table.setVisible(False)
            self._update_metrics(0, 0)
            QMessageBox.information(self, "Info", "No line/model data found for the selected filters.")
            return

        data = []
        for rp in rows_pairs:
            line_val = rp['line']
            model_val = rp['model']
            canonical_model = normalize_model(model_val)
            variants = get_variants(canonical_model)
            placeholders = ','.join(['?'] * len(variants))

            params1 = base_params1 + variants + [line_val]
            query1 = f"""
                SELECT SUM({metric_column}) as value
                FROM rework_root_cause
                WHERE record_date BETWEEN ? AND ? {where_clause}
                AND model IN ({placeholders})
                AND line = ?
            """
            row1 = self.db.execute_query(query1, tuple(params1), fetch_one=True) or {}
            q1 = safe_int(row1.get('value'))

            params2 = base_params2 + variants + [line_val]
            query2 = f"""
                SELECT SUM({metric_column}) as value
                FROM rework_root_cause
                WHERE record_date BETWEEN ? AND ? {where_clause}
                AND model IN ({placeholders})
                AND line = ?
            """
            row2 = self.db.execute_query(query2, tuple(params2), fetch_one=True) or {}
            q2 = safe_int(row2.get('value'))

            diff = q2 - q1
            pct_change = (diff / q1 * 100) if q1 != 0 else (100 if q2 > 0 else 0)
            data.append({
                'line': line_val,
                'model': canonical_model,
                'q1': q1,
                'q2': q2,
                'diff': diff,
                'pct_change': pct_change
            })

        data.sort(key=lambda x: (x['line'], x['model']))

        month1_label = self.month1_start.date().toString("MMM yyyy")
        month2_label = self.month2_start.date().toString("MMM yyyy")
        metric_label = selected_metric.capitalize()

        self.compare_table.clearContents()
        self.compare_table.setRowCount(len(data))
        self.compare_table.setColumnCount(6)
        self.compare_table.setHorizontalHeaderLabels([
            "Line", "Model",
            f"{month1_label} {metric_label}",
            f"{month2_label} {metric_label}",
            "Difference",
            "% Change"
        ])

        grand_m1 = 0
        grand_m2 = 0
        for i, d in enumerate(data):
            self.compare_table.setItem(i, 0, QTableWidgetItem(d['line']))
            self.compare_table.setItem(i, 1, QTableWidgetItem(d['model']))
            self.compare_table.setItem(i, 2, QTableWidgetItem(f"{d['q1']:,}"))
            self.compare_table.setItem(i, 3, QTableWidgetItem(f"{d['q2']:,}"))
            self.compare_table.setItem(i, 4, QTableWidgetItem(f"{d['diff']:+,}"))
            pct_item = QTableWidgetItem(f"{d['pct_change']:+.1f}%")
            if d['diff'] > 0:
                pct_item.setForeground(QColor("#15803d"))
            elif d['diff'] < 0:
                pct_item.setForeground(QColor("#b91c1c"))
            self.compare_table.setItem(i, 5, pct_item)
            grand_m1 += d['q1']
            grand_m2 += d['q2']

        self.compare_table.resizeColumnsToContents()
        self.compare_table.setVisible(True)
        self._update_metrics(grand_m1, grand_m2)

    # ------------------------------------------------------------------
    # PDF Export for Monthly Comparison
    # ------------------------------------------------------------------
    def export_monthly_compare_pdf(self):
        if self.compare_table.rowCount() == 0:
            CustomMessageBox.show_warning(self, "Warning", "No data to export. Please run a comparison first.")
            return

        # ---------- collect table data ----------
        headers = []
        for col in range(self.compare_table.columnCount()):
            headers.append(self.compare_table.horizontalHeaderItem(col).text())

        data = []
        for row in range(self.compare_table.rowCount()):
            row_data = []
            for col in range(self.compare_table.columnCount()):
                item = self.compare_table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        # ---------- filter info ----------
        month1_label = self.month1_start.date().toString("MMMM yyyy")
        month2_label = self.month2_start.date().toString("MMMM yyyy")
        line = self.compare_line_combo.currentText()
        model = self.compare_model_combo.currentText()
        metric = self.metric_combo.currentText().capitalize()
        gen_date = datetime.datetime.now().strftime("%d %B %Y  %H:%M")

        # ---------- compute totals ----------
        total_m1 = 0
        total_m2 = 0
        
        for row_data in data:
            if row_data[0] in ("TOTAL", "GRAND TOTAL"):
                try:
                    if len(headers) == 6:
                        total_m1 = int(row_data[2].replace(",", ""))
                        total_m2 = int(row_data[3].replace(",", ""))
                    elif len(headers) == 5:
                        total_m1 = int(row_data[1].replace(",", ""))
                        total_m2 = int(row_data[2].replace(",", ""))
                except:
                    pass
                continue
            try:
                if len(headers) == 6:
                    total_m1 += int(row_data[2].replace(",", ""))
                    total_m2 += int(row_data[3].replace(",", ""))
                elif len(headers) == 5:
                    total_m1 += int(row_data[1].replace(",", ""))
                    total_m2 += int(row_data[2].replace(",", ""))
            except:
                pass

        diff = total_m2 - total_m1
        pct_change = (diff / total_m1 * 100) if total_m1 != 0 else (100 if total_m2 > 0 else 0)

        # Determine color class for summary: for REWORK, decrease is GOOD
        if diff > 0:
            diff_class = "negative"      # More rework = BAD
        elif diff < 0:
            diff_class = "positive"      # Less rework = GOOD
        else:
            diff_class = ""

        # ---------- CSS (table-based layout for PDF compatibility) ----------
        css = """
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
                font-size: 10pt;
                color: #1E293B;
                margin: 0;
                padding: 30px 40px;
                background: #fff;
            }
            .company-header {
                text-align: left;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 3px solid #1E3A8A;
            }
            .company-name {
                font-size: 18pt;
                font-weight: 700;
                color: #1E3A8A;
                letter-spacing: 1px;
            }
            .report-title {
                font-size: 12pt;
                font-weight: 600;
                color: #334155;
                margin-top: 2px;
            }
            
            /* PDF-safe info bar using table */
            .info-bar {
                width: 100%;
                background: #F1F5F9;
                border-radius: 6px;
                padding: 8px 14px;
                margin: 12px 0 15px 0;
                font-size: 8.5pt;
                color: #334155;
            }
            .info-bar td {
                border: none;
                padding: 2px 0;
                font-weight: 500;
            }
            
            /* PDF-safe summary using table */
            .summary-box {
                width: 100%;
                margin-bottom: 20px;
                padding: 10px 15px;
                background: #F8FAFC;
                border-radius: 6px;
                border: 1px solid #E2E8F0;
            }
            .summary-box td {
                border: none;
                text-align: center;
                vertical-align: middle;
                padding: 5px 10px;
            }
            .metric-label {
                font-size: 8.5pt;
                color: #64748B;
                font-weight: 500;
                display: block;
            }
            .metric-value {
                font-size: 12pt;
                font-weight: 700;
                color: #1E293B;
                display: block;
            }
            .metric-value.positive {
                color: #059669;
            }
            .metric-value.negative {
                color: #DC2626;
            }
            .metric-divider {
                color: #CBD5E1;
                font-weight: 300;
                font-size: 14pt;
                width: 1px;
            }
            
            table.data-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 8.5pt;
                table-layout: auto;
            }
            th {
                background: #1E3A8A;
                color: #FFFFFF;
                padding: 6px 8px;
                font-weight: 600;
                text-align: left;
                border: 1px solid #1E3A8A;
                font-size: 8pt;
            }
            td {
                border: 1px solid #CBD5E1;
                padding: 5px 8px;
                vertical-align: middle;
            }
            td:last-child, th:last-child {
                text-align: center;
            }
            td:nth-child(3), td:nth-child(4), td:nth-child(5), td:nth-child(6) {
                text-align: right;
            }
            tr:nth-child(even) {
                background-color: #F8FAFC;
            }
            .total-row {
                background-color: #DBEAFE !important;
                font-weight: 700;
                border-top: 2px solid #1E3A8A;
            }
            .positive {
                color: #059669;
                font-weight: 600;
            }
            .negative {
                color: #DC2626;
                font-weight: 600;
            }
            .footer {
                margin-top: 25px;
                padding-top: 12px;
                border-top: 1px solid #E2E8F0;
                text-align: center;
                font-size: 7.5pt;
                color: #64748B;
            }
            tr {
                page-break-inside: avoid;
            }
            thead {
                display: table-header-group;
            }
        </style>
        """

        # ---------- build HTML ----------
        html = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            {css}
        </head>
        <body>

        <!-- HEADER -->
        <div class="company-header">
            <div class="company-name">SSH FACTORY</div>
            <div class="report-title">Monthly Rework Comparison Report – {metric}</div>
        </div>

        <!-- INFO BAR (table-based for PDF) -->
        <table class="info-bar">
            <tr>
                <td>Period: {month1_label} vs {month2_label}</td>
                <td>Line: {line if line != 'All Lines' else 'All'}</td>
                <td>Model: {model if model != 'All Models' else 'All'}</td>
                <td style="text-align:right;">Generated: {gen_date}</td>
            </tr>
        </table>

        <!-- SUMMARY - table-based for PDF compatibility -->
        <table class="summary-box">
            <tr>
                <td>
                    <span class="metric-label">{month1_label}</span>
                    <span class="metric-value">{total_m1:,}</span>
                    <span class="metric-label">units</span>
                </td>
                <td class="metric-divider">|</td>
                <td>
                    <span class="metric-label">{month2_label}</span>
                    <span class="metric-value">{total_m2:,}</span>
                    <span class="metric-label">units</span>
                </td>
                <td class="metric-divider">|</td>
                <td>
                    <span class="metric-label">Change</span>
                    <span class="metric-value {diff_class}">
                        {diff:+,}
                    </span>
                    <span class="metric-label">({pct_change:+.1f}%)</span>
                </td>
            </tr>
        </table>

        <!-- TABLE -->
        <table class="data-table" cellspacing="0">
            <thead>
                <tr>
        """

        for h in headers:
            html += f"<th>{h}</th>"
        html += "</tr></thead><tbody>"

        for idx, row_data in enumerate(data):
            is_total = row_data[0] in ("TOTAL", "GRAND TOTAL")
            row_class = 'class="total-row"' if is_total else ""
            html += f"<tr {row_class}>"
            for col_idx, cell in enumerate(row_data):
                # styling for % change column
                if col_idx == len(row_data) - 1 and cell.endswith('%'):
                    if cell.startswith('+'):
                        html += f'<td class="negative">{cell}</td>'      # More rework = BAD
                    elif cell.startswith('-'):
                        html += f'<td class="positive">{cell}</td>'      # Less rework = GOOD
                    else:
                        html += f"<td>{cell}</td>"
                else:
                    html += f"<td>{cell}</td>"
            html += "</tr>"

        html += f"""
                </tbody>
            </table>

            <!-- FOOTER -->
            <div class="footer">
                This report is system‑generated. Data accuracy depends on input records.<br>
                Report includes all rework entries within the selected date ranges.
            </div>

        </body>
        </html>
        """

        self._print_html(html)        
    # ------------------------------------------------------------------
    # Data loading methods for Inspections, Rework, etc.
    # ------------------------------------------------------------------
    def load_inspections(self):
        """Load inspections – employee name is taken ONLY from remarks (user‑entered value)."""
        self.all_data = []
        try:
            # No JOIN with users – we only use the remarks field
            rows = self.db.execute_query("""
                SELECT *
                FROM inspections
                WHERE inspection_type IN ('MMI Test','Semi Test','Appearance Test','Final Test')
                ORDER BY inspection_date DESC
            """, fetch_all=True)

            if not rows:
                self.report_table.setRowCount(1)
                no_item = QTableWidgetItem("No inspection records found.")
                no_item.setTextAlignment(Qt.AlignCenter)
                self.report_table.setItem(0, 0, no_item)
                self.records_count.setText("📊 0")
                self.footer_label.setText("No records")
                return

            col_names = list(rows[0].keys()) if rows else []
            has_ship = 'ship' in col_names
            has_model = 'model' in col_names
            has_phone_type = 'phone_type' in col_names

            for row in rows:
                defects_text = row.get('defects') or ""
                faults = self._parse_faults(defects_text)
                recalc = sum(faults.values())
                rej = row.get('rejected_quantity') or 0
                defects_count = recalc if recalc > 0 else rej
                if rej > 0 and not faults:
                    faults["Total Faults"] = rej

                remarks = row.get('remarks') or ""
                insp_date = row.get('inspection_date') or datetime.datetime.now()

                # ---- Get model & ship from direct columns or remarks ----
                model = row.get('model') if has_model else None
                if not model:
                    model = self._extract(remarks, "Model:") or "N/A"
                ship = row.get('ship') if has_ship else None
                if not ship:
                    ship = self._extract(remarks, "Shipment:") or "N/A"
                color = self._extract(remarks, "Color:") or ""

                # ---- Get employee name ONLY from remarks ----
                employee = self._extract_employee_from_remarks(remarks)
                if not employee:
                    employee = "N/A"

                # ---- Get employee ID / Tester ID ----
                employee_id = self._extract(remarks, "Tester ID:") or self._extract(remarks, "Employee ID:") or "N/A"
                line = row.get('line') or "N/A"
                floor = row.get('floor') or "N/A"
                phone_type = row.get('phone_type') if has_phone_type else "Feature"
                if not phone_type:
                    phone_type = "Feature"

                self.all_data.append({
                    'date': insp_date.strftime('%Y-%m-%d'),
                    'time': insp_date.strftime('%H:%M:%S'),
                    'station': row.get('inspection_type') or 'MMI Test',
                    'model': model,
                    'ship': ship,
                    'color': color,
                    'employee': employee,
                    'employee_id': employee_id,
                    'line': line,
                    'floor': floor,
                    'defects_count': defects_count,
                    'faults': faults,
                    'inspection_code': row.get('inspection_code') or '',
                    'phone_type': phone_type,   # <-- added
                })

        except Exception as e:
            CustomMessageBox.show_error(self, "Database Error", f"Failed to load inspections:\n{str(e)}")
            self.report_table.setRowCount(1)
            self.report_table.setSpan(0, 0, 1, 9)
            self.report_table.setItem(0, 0, QTableWidgetItem(f"Error: {str(e)}"))
            return

        self.generate_inspection_report()

    def _extract_employee_from_remarks(self, remarks):
        """Try multiple patterns to extract employee name from remarks."""
        if not remarks:
            return None
        
        patterns = [
            r'Employee\s*Name\s*:\s*([^,]+)',
            r'Employee\s*:\s*([^,]+)',
            r'Employee\s*([^,]+)',
            r'Inspector\s*:\s*([^,]+)',
            r'Operator\s*:\s*([^,]+)',
            r'User\s*:\s*([^,]+)',
            r'Name\s*:\s*([^,]+)',
        ]
        for pat in patterns:
            match = re.search(pat, remarks, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if name:
                    return name
        return None

    def _parse_faults(self, txt):
        """Parse defects text into dictionary of fault: count."""
        faults = {}
        if not txt or txt == "No defects":
            return faults

        if '\n' in txt:
            lines = txt.split('\n')
        else:
            lines = [txt]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for rework format with '| PCB:'
            if ' | PCB:' in line:
                parts = line.split(' | ')
                fault_name = parts[0].strip()
                total_qty = 0
                for part in parts[1:]:
                    if ':' in part:
                        try:
                            qty = int(part.split(':')[1].strip())
                            total_qty += qty
                        except (ValueError, IndexError):
                            pass
                if fault_name and total_qty > 0:
                    faults[fault_name] = total_qty
                continue

            # Try patterns: "fault: qty" or "fault qty"
            m = re.match(r'^(.+?):\s*(\d+)\s*(?:pcs)?$', line, re.I)
            if m:
                faults[m.group(1).strip()] = int(m.group(2))
                continue

            m2 = re.match(r'^(.+?)\s+(\d+)\s*$', line)
            if m2:
                faults[m2.group(1).strip()] = int(m2.group(2))
                continue

            # Handle comma-separated faults (e.g., "LCD BLACK: 2, LCD WHITE: 1")
            if ',' in line:
                for part in line.split(','):
                    part = part.strip()
                    m3 = re.match(r'^(.+?):\s*(\d+)\s*(?:pcs)?$', part, re.I)
                    if m3:
                        faults[m3.group(1).strip()] = int(m3.group(2))

        return faults

    def _get_category(self, fault_name):
        """Derive broader category for a fault name (used for manual entries)"""
        if not fault_name:
            return 'OTHER'
        fault_name = fault_name.strip().upper()
        # Try exact match first
        for key, value in self.FAULT_CATEGORY_MAP.items():
            if key.upper() == fault_name:
                return value
        # Try partial match
        for key, value in self.FAULT_CATEGORY_MAP.items():
            if key.upper() in fault_name or fault_name in key.upper():
                return value
        return self.FAULT_CATEGORY_MAP.get('DEFAULT', 'OTHER')

    def _update_metrics(self, total_m1, total_m2):
        """Update the summary metrics labels for monthly comparison."""
        diff = total_m2 - total_m1
        pct_change = (diff / total_m1 * 100) if total_m1 != 0 else (100 if total_m2 > 0 else 0)
        month1_name = self.month1_start.date().toString("MMM yyyy")
        month2_name = self.month2_start.date().toString("MMM yyyy")
        self.m1_metric_label.setText(f"📅 {month1_name}: {total_m1:,}")
        self.m2_metric_label.setText(f"📅 {month2_name}: {total_m2:,}")
        self.diff_metric_label.setText(f"📊 Difference: {diff:+,}")
        self.diff_metric_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {'#059669' if diff >= 0 else '#dc2626'};")
        self.pct_metric_label.setText(f"📈 % Change: {pct_change:+.1f}%")
        self.pct_metric_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {'#059669' if pct_change >= 0 else '#dc2626'};")

    def _extract(self, text, key):
        """Extract value after key, handling commas inside values."""
        if not text:
            return None
        pattern = rf'{key}\s*([^,]+?)(?=\s*,\s*\w+:|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def generate_inspection_report(self):
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        station = self.station_filter.currentText()
        search_text = self.search_input.text().lower()
        self.filtered_data = []
        for r in self.all_data:
            if r['date'] < date_from or r['date'] > date_to:
                continue
            if station != "All" and r['station'] != station:
                continue
            if search_text:
                found = any(search_text in str(r.get(f,'')).lower() for f in ['model','employee','employee_id','line','floor'])
                if not found:
                    found = any(search_text in f.lower() for f in r['faults'].keys())
                if not found:
                    continue
            self.filtered_data.append(r)
        self._update_table(self.filtered_data)
        self.records_count.setText(f"📊 {len(self.filtered_data)}")
        self.footer_label.setText(f"Showing {len(self.filtered_data)} of {len(self.all_data)} records")
        if self.filtered_data:
            total_f = sum(d['defects_count'] for d in self.filtered_data)
            self.quick_stats.setText(f"⚡ Total Faults: {total_f} | Avg: {total_f/len(self.filtered_data):.1f}")

    def _update_table(self, data):
        self.report_table.setRowCount(len(data))
        for row, rec in enumerate(data):
            for col,key in enumerate(['date','time','station','model','employee','employee_id','line','floor']):
                self.report_table.setItem(row,col, QTableWidgetItem(str(rec[key])))
            cnt = rec['defects_count']
            btn = QPushButton(f"⚠ {cnt}" if cnt else "✓ 0")
            btn.setFixedSize(80,28)
            if cnt == 0:
                btn.setStyleSheet("background: #10B981; color: white; border-radius: 14px; font-weight: bold;")
            elif cnt <= 5:
                btn.setStyleSheet("background: #F59E0B; color: white; border-radius: 14px; font-weight: bold;")
            else:
                btn.setStyleSheet("background: #EF4444; color: white; border-radius: 14px; font-weight: bold;")
            btn.clicked.connect(lambda _,f=rec['faults']: FaultDetailsDialog(f,self).exec_())
            self.report_table.setCellWidget(row,8,btn)

    def on_row_double_clicked(self, item):
        row = item.row()
        if row < len(self.filtered_data):
            self.open_edit_dialog(self.filtered_data[row])

    def open_edit_dialog(self, rec):
        from widgets.new_entry_widget import NewEntryWidget
        
        inspection_code = rec.get('inspection_code')
        if not inspection_code:
            CustomMessageBox.show_warning(self, "Error", "No inspection code found.")
            return
        
        # ڈیٹا بیس سے مکمل ریکارڈ حاصل کریں
        try:
            row = self.db.execute_query(
                "SELECT * FROM inspections WHERE inspection_code = ?",
                (inspection_code,), fetch_one=True
            )
            if not row:
                CustomMessageBox.show_warning(self, "Error", "Inspection not found in database.")
                return
        except Exception as e:
            CustomMessageBox.show_error(self, "Database Error", f"Could not fetch record: {str(e)}")
            return
        
        # ریکارڈ کو پارس کریں
        defects_text = row.get('defects') or ""
        faults = self._parse_faults(defects_text)
        rej = row.get('rejected_quantity') or 0
        defects_count = sum(faults.values()) if faults else rej
        if rej > 0 and not faults:
            faults = {"Total Faults": rej}
        
        remarks = row.get('remarks') or ""
        insp_date = row.get('inspection_date') or datetime.datetime.now()
        
        # ایکسٹرکشن (پہلے سے موجود طریقے استعمال کریں)
        model = row.get('model') or self._extract(remarks, "Model:") or "N/A"
        ship = row.get('ship') or self._extract(remarks, "Shipment:") or "N/A"
        color = self._extract(remarks, "Color:") or ""
        employee = self._extract_employee_from_remarks(remarks) or "N/A"
        employee_id = self._extract(remarks, "Tester ID:") or self._extract(remarks, "Employee ID:") or "N/A"
        line = row.get('line') or "N/A"
        floor = row.get('floor') or "N/A"
        phone_type = row.get('phone_type') or "Feature"
        station = row.get('inspection_type') or "MMI Test"
        
        edit_data = {
            'inspection_code': inspection_code,
            'station': station,
            'model': model,
            'ship': ship,
            'color': color,
            'employee': employee,
            'tester_id': employee_id,
            'line': line,
            'floor': floor,
            'faults': faults,
            'defects_count': defects_count,
            'inspection_date': insp_date.strftime('%Y-%m-%d'),
            'phone_type': phone_type,
        }
        
        # ڈیبگ پرنٹ (تاکہ پتہ چل سکے کہ کیا آیا)
        print("\n=== Edit Dialog Data (from DB) ===")
        for k, v in edit_data.items():
            if k == 'faults':
                print(f"  {k}: {v} (count: {len(v)})")
            else:
                print(f"  {k}: {v}")
        print("===================================\n")
        
        dlg = QDialog(self)
        dlg.setWindowTitle("✏️ Edit Inspection Record")
        dlg.setModal(True)
        
        widget = NewEntryWidget(
            self.db,
            {'id': self.user_role, 'full_name': 'Admin', 'role': self.user_role},
            edit_mode=True,
            edit_data=edit_data
        )
        layout = QVBoxLayout(dlg)
        layout.addWidget(widget)
        widget.data_saved.connect(lambda: (dlg.accept(), self.load_inspections(), CustomMessageBox.show_success(self, "Success", "Record updated!")))
        dlg.showMaximized()
        dlg.exec_()

    # ------------------------------------------------------------------
    # LOAD COMPLETED REWORK (with ID and category mapping)
    # ------------------------------------------------------------------
    def load_completed_rework(self):
        line = self.rework_line_filter.text().strip()
        model = self.rework_model_filter.text().strip()
        query = "SELECT id, record_date, [line], model, fault_category, fault_subcategory, pcba_qty, material_qty, fixing_qty, soldering_qty, total_qty FROM rework_root_cause WHERE 1=1"
        params = []
        if line: 
            query += " AND [line] LIKE ?"
            params.append(f"%{line}%")
        if model: 
            query += " AND model LIKE ?"
            params.append(f"%{model}%")
        rows = self.db.execute_query(query, tuple(params), fetch_all=True)
        
        headers = ["ID", "Date", "Line", "Model", "Fault Category", "Sub Fault", "PCBA", "Material", "Fixing", "Soldering", "Total"]
        self.rework_table.setColumnCount(len(headers))
        self.rework_table.setHorizontalHeaderLabels(headers)
        self.rework_table.setColumnHidden(0, True)  # ID column hide
        
        if not rows:
            self.rework_table.setRowCount(1)
            self.rework_table.setSpan(0,0,1,len(headers))
            no_item = QTableWidgetItem("No rework root cause data found. Import via ReworkWidget.")
            no_item.setTextAlignment(Qt.AlignCenter)
            self.rework_table.setItem(0,0, no_item)
            self.rework_total_label.setText("Total Units: 0")
            return
        
        self.rework_table.setRowCount(len(rows))
        total = 0
        
        for i, r in enumerate(rows):
            self.rework_table.setItem(i, 0, QTableWidgetItem(str(r['id'])))
            date_str = r['record_date'].strftime('%Y-%m-%d') if r['record_date'] else ''
            self.rework_table.setItem(i, 1, QTableWidgetItem(date_str))
            self.rework_table.setItem(i, 2, QTableWidgetItem(str(r['line'])))
            self.rework_table.setItem(i, 3, QTableWidgetItem(str(r['model'])))
            
            fault_name = r['fault_category'] or ''
            sub_fault = r['fault_subcategory'] or ''
            
            if not sub_fault and fault_name:
                category = self._get_category(fault_name)
                sub_fault = fault_name
            else:
                category = fault_name
            
            self.rework_table.setItem(i, 4, QTableWidgetItem(str(category)))
            self.rework_table.setItem(i, 5, QTableWidgetItem(str(sub_fault)))
            
            for col, key in enumerate(['pcba_qty', 'material_qty', 'fixing_qty', 'soldering_qty', 'total_qty'], start=6):
                val = r[key] or 0
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.rework_table.setItem(i, col, item)
                if key == 'total_qty':
                    total += val
        
        self.rework_total_label.setText(f"Total Units: {total}")
        widths = [0, 90, 80, 100, 120, 150, 60, 60, 60, 60, 70]
        for i, w in enumerate(widths):
            self.rework_table.setColumnWidth(i, w)

    # ------------------------------------------------------------------
    # DELETE METHODS (Permanent Deletion from Database)
    # ------------------------------------------------------------------
    def delete_selected_inspection(self):
        selected = self.report_table.currentRow()
        if selected < 0 or selected >= len(self.filtered_data):
            CustomMessageBox.show_warning(self, "Warning", "Please select a row first.")
            return
        
        rec = self.filtered_data[selected]
        inspection_code = rec.get('inspection_code')
        if not inspection_code:
            CustomMessageBox.show_warning(self, "Warning", "Cannot identify inspection record.")
            return
        
        reply = CustomMessageBox.show_question(
            self,
            "⚠️ Confirm Permanent Delete",
            f"Are you sure you want to permanently delete this inspection record?\n\n"
            f"📋 Code: {inspection_code}\n"
            f"📅 Date: {rec.get('date')}\n"
            f"📱 Model: {rec.get('model')}\n"
            f"👤 Employee: {rec.get('employee')}\n\n"
            "⚠️ This will also delete:\n"
            "• All linked defects\n"
            "• All linked rework tasks\n"
            "• All linked rework details\n\n"
            "This action CANNOT be undone!"
        )
        
        if reply != QDialog.Accepted:
            return
        
        try:
            insp = self.db.execute_query(
                "SELECT id FROM inspections WHERE inspection_code = ?",
                (inspection_code,), fetch_one=True
            )
            if not insp:
                CustomMessageBox.show_error(self, "Error", "Inspection record not found in database.")
                return
            
            insp_id = insp['id']
            
            with self.db.get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM rework_tasks WHERE inspection_id = ?", (insp_id,))
                c.execute("DELETE FROM rework_details WHERE inspection_id = ?", (insp_id,))
                c.execute("DELETE FROM defects WHERE inspection_id = ?", (insp_id,))
                c.execute("DELETE FROM inspections WHERE id = ?", (insp_id,))
                conn.commit()
            
            CustomMessageBox.show_success(self, "Success", f"✅ Inspection {inspection_code} and all linked data deleted successfully.")
            self.load_inspections()
            
        except Exception as e:
            CustomMessageBox.show_error(self, "Delete Error", f"Failed to delete inspection:\n{str(e)}")

    def delete_selected_rework_record(self):
        selected = self.rework_table.currentRow()
        if selected < 0:
            CustomMessageBox.show_warning(self, "Warning", "Please select a row first.")
            return
        
        record_id_item = self.rework_table.item(selected, 0)
        if not record_id_item:
            CustomMessageBox.show_warning(self, "Warning", "Could not retrieve record ID.")
            return
        
        record_id = int(record_id_item.text())
        date = self.rework_table.item(selected, 1).text() if self.rework_table.item(selected, 1) else ""
        line = self.rework_table.item(selected, 2).text() if self.rework_table.item(selected, 2) else ""
        model = self.rework_table.item(selected, 3).text() if self.rework_table.item(selected, 3) else ""
        fault_cat = self.rework_table.item(selected, 4).text() if self.rework_table.item(selected, 4) else ""
        
        reply = CustomMessageBox.show_question(
            self,
            "⚠️ Confirm Permanent Delete",
            f"Are you sure you want to permanently delete this rework record?\n\n"
            f"🆔 ID: {record_id}\n"
            f"📅 Date: {date}\n"
            f"📍 Line: {line}\n"
            f"📱 Model: {model}\n"
            f"⚠️ Fault: {fault_cat}\n\n"
            "This action CANNOT be undone!"
        )
        
        if reply != QDialog.Accepted:
            return
        
        try:
            self.db.execute_query("DELETE FROM rework_root_cause WHERE id = ?", (record_id,))
            CustomMessageBox.show_success(self, "Success", f"✅ Record ID {record_id} deleted successfully.")
            self.load_completed_rework()
            self.load_rework_report()
            self.load_inspections()
        except Exception as e:
            CustomMessageBox.show_error(self, "Delete Error", f"Failed to delete record:\n{str(e)}")

    # ------------------------------------------------------------------
    # Rework Report (Tab3) – unchanged
    # ------------------------------------------------------------------
    def load_rework_report(self):
        for i in reversed(range(self.report_layout.count())):
            w = self.report_layout.itemAt(i).widget()
            if w: w.deleteLater()
        date_from = self.report_date_from.date().toString("yyyy-MM-dd")
        date_to = self.report_date_to.date().toString("yyyy-MM-dd")
        line = self.report_line_filter.currentText()
        model = self.report_model_filter.currentText()
        fault = self.report_fault_filter.currentText()
        query = "SELECT line, model, fault_category, fault_subcategory, pcba_qty, material_qty, fixing_qty, soldering_qty, total_qty FROM rework_root_cause WHERE record_date BETWEEN ? AND ?"
        params = [date_from, date_to]
        if line!="All": query += " AND line=?"; params.append(line)
        if model!="All": query += " AND model=?"; params.append(model)
        if fault!="All": query += " AND fault_category=?"; params.append(fault)
        rows = self.db.execute_query(query, tuple(params), fetch_all=True)
        if not rows:
            self.report_layout.addWidget(QLabel("⚠️ No rework data found for the selected filters. Change date range or filter criteria."))
            self.report_total_label.setText("Total: 0 units")
            self.summary_card.setVisible(False)
            return
        groups = {}
        grand = {'pcba':0,'material':0,'fixing':0,'soldering':0,'total':0}
        for r in rows:
            key = (r['line'], r['model'])
            groups.setdefault(key, []).append({
                'fault_category': r['fault_category'] or "General",
                'fault_subcategory': r['fault_subcategory'] or "",
                'pcba': r['pcba_qty'] or 0, 'material': r['material_qty'] or 0,
                'fixing': r['fixing_qty'] or 0, 'soldering': r['soldering_qty'] or 0,
                'total': r['total_qty'] or 0
            })
            for k in grand: grand[k] += r[f'{k}_qty'] if k!='total' else r['total_qty'] or 0
        for (line_name, model_name), faults in groups.items():
            group = QGroupBox(f"  LINE: {line_name}  |  MODEL: {model_name}  ")
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    font-size: 13px;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    margin-top: 10px;
                    background: white;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 15px;
                    padding: 0 10px;
                    background: #0f2027;
                    color: white;
                    border-radius: 12px;
                }
            """)
            vbox = QVBoxLayout(group)
            table = QTableWidget()
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels(["Fault Category","Sub Fault","PCBA","Material","Fixing","Soldering","Total"])
            table.setAlternatingRowColors(True)
            table.setStyleSheet("""
                QTableWidget {
                    border: 1px solid #cbd5e1;
                    background: white;
                    border-radius: 6px;
                }
                QHeaderView::section {
                    background: #334155;
                    color: white;
                    padding: 6px;
                    font-weight: bold;
                    font-size: 11px;
                }
            """)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setRowCount(len(faults)+1)
            row_totals = {'pcba':0,'material':0,'fixing':0,'soldering':0,'total':0}
            for i,f in enumerate(sorted(faults, key=lambda x:x['fault_category'])):
                table.setItem(i,0, QTableWidgetItem(f['fault_category']))
                table.setItem(i,1, QTableWidgetItem(f['fault_subcategory']))
                for col,key in enumerate(['pcba','material','fixing','soldering','total'],2):
                    val = f[key]
                    item = QTableWidgetItem(f"{val:,}")
                    item.setTextAlignment(Qt.AlignRight)
                    table.setItem(i,col, item)
                    row_totals[key] += val
            total_item = QTableWidgetItem("TOTAL")
            total_item.setFont(QFont("Segoe UI",10,QFont.Bold))
            total_item.setBackground(QColor("#f1f5f9"))
            table.setItem(len(faults),0, total_item)
            table.setSpan(len(faults),0,1,2)
            for col,key in enumerate(['pcba','material','fixing','soldering','total'],2):
                titem = QTableWidgetItem(f"{row_totals[key]:,}")
                titem.setFont(QFont("Segoe UI",10,QFont.Bold))
                titem.setBackground(QColor("#f1f5f9"))
                titem.setTextAlignment(Qt.AlignRight)
                table.setItem(len(faults),col, titem)
            table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            table.horizontalHeader().setStretchLastSection(True)
            table.resizeColumnsToContents()
            vbox.addWidget(table)
            self.report_layout.addWidget(group)
        grand_box = QGroupBox("GRAND TOTAL")
        grand_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #0f2027;
                border-radius: 8px;
                margin-top: 10px;
                background: #fef9e3;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 12px;
                background: #0f2027;
                color: white;
                border-radius: 12px;
            }
        """)
        grand_layout = QVBoxLayout(grand_box)
        grand_table = QTableWidget()
        grand_table.setColumnCount(6)
        grand_table.setHorizontalHeaderLabels(["Metric","PCBA","Material","Fixing","Soldering","Total"])
        grand_table.setRowCount(1)
        grand_table.setItem(0,0, QTableWidgetItem("All Faults"))
        for col,key in enumerate(['pcba','material','fixing','soldering','total'],1):
            item = QTableWidgetItem(f"{grand[key]:,}")
            item.setFont(QFont("Segoe UI",11,QFont.Bold))
            item.setTextAlignment(Qt.AlignRight)
            grand_table.setItem(0,col, item)
        grand_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grand_table.horizontalHeader().setStretchLastSection(True)
        grand_table.resizeColumnsToContents()
        grand_layout.addWidget(grand_table)
        self.report_layout.addWidget(grand_box)
        self.report_total_label.setText(f"Total: {grand['total']:,} units")
        filter_text = f"Line: {line if line!='All' else 'All'} | Model: {model if model!='All' else 'All'} | Fault: {fault if fault!='All' else 'All'}"
        self.summary_label.setText(f"📋 {len(groups)} group(s) | Filters: {filter_text} | Period: {date_from} to {date_to}")
        self.summary_card.setVisible(True)

    # ------------------------------------------------------------------
    # Print & Export helpers (CSV, Excel, HTML)
    # ------------------------------------------------------------------
    def print_rework_report(self):
        html = self._build_report_html()
        if html: self._print_html(html)

    def _build_report_html(self):
        date_from = self.report_date_from.date().toString("yyyy-MM-dd")
        date_to = self.report_date_to.date().toString("yyyy-MM-dd")
        line = self.report_line_filter.currentText()
        model = self.report_model_filter.currentText()
        fault = self.report_fault_filter.currentText()

        query = """
            SELECT record_date, line, model, fault_category, fault_subcategory,
                pcba_qty, material_qty, fixing_qty, soldering_qty, total_qty
            FROM rework_root_cause WHERE record_date BETWEEN ? AND ?
        """
        params = [date_from, date_to]
        if line != "All":
            query += " AND line=?"
            params.append(line)
        if model != "All":
            query += " AND model=?"
            params.append(model)
        if fault != "All":
            query += " AND fault_category=?"
            params.append(fault)

        rows = self.db.execute_query(query, tuple(params), fetch_all=True)
        if not rows:
            return None
        groups = {}
        grand = {'pcba': 0, 'material': 0, 'fixing': 0, 'soldering': 0, 'total': 0}
        for r in rows:
            key = (r['line'], r['model'])
            groups.setdefault(key, []).append({
                'date': r['record_date'].strftime('%Y-%m-%d') if r['record_date'] else '',
                'cat': r['fault_category'] or '', 'sub': r['fault_subcategory'] or '',
                'pcba': r['pcba_qty'] or 0, 'material': r['material_qty'] or 0,
                'fix': r['fixing_qty'] or 0, 'sold': r['soldering_qty'] or 0,
                'total': r['total_qty'] or 0
            })
            for k in grand:
                grand[k] += r[f'{k}_qty'] if k != 'total' else r['total_qty'] or 0
        css = """
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
                margin: 0;
                padding: 5mm;
                width: 100%;
            }
            h2 { text-align: center; margin-bottom: 10px; color: #0f2027; }
            h3 { background: #e2e8f0; padding: 5px 10px; margin: 15px 0 10px 0; font-size: 12pt; }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 15px;
                font-size: 9pt;
                table-layout: fixed;
            }
            th, td { border: 1px solid #999; padding: 4px 6px; text-align: left; vertical-align: top; word-wrap: break-word; }
            th { background: #d9e2f3; font-weight: bold; }
            .right { text-align: right; }
            .group-total { background: #fff2cc; font-weight: bold; }
            @media print {
                @page { margin: 5mm; size: A4 landscape; }
                body { font-size: 12pt; }
                h2 { font-size: 18pt; }
                h3 { font-size: 14pt; background: #eee; }
                table { font-size: 11pt; table-layout: auto; }
                th { background: #ccc !important; color: black !important; }
                .group-total { background: #ffffcc !important; }
            }
        </style>
        """
        html = f"<html><head>{css}</head><body>"
        html += f"<h2>SSH FACTORY - REWORK REPORT<br><small>{date_from} TO {date_to}</small></h2>"
        for (l, m), flist in groups.items():
            html += f"<h3>Line: {l} | Model: {m}</h3>"
            html += "<table><thead><tr><th style='width:12%'>Date</th><th style='width:20%'>Fault Cat</th><th style='width:20%'>Sub Fault</th><th style='width:12%'>PCBA</th><th style='width:12%'>Material</th><th style='width:12%'>Fixing</th><th style='width:12%'>Soldering</th><th style='width:12%'>Total</th></tr></thead><tbody>"
            group_total = {'pcba':0, 'material':0, 'fix':0, 'sold':0, 'total':0}
            for f in flist:
                for k in group_total:
                    group_total[k] += f[k]
                html += f"""
                <tr>
                    <td>{f['date']}</td>
                    <td>{f['cat']}</td>
                    <td>{f['sub']}</td>
                    <td class='right'>{f['pcba']:,}</td>
                    <td class='right'>{f['material']:,}</td>
                    <td class='right'>{f['fix']:,}</td>
                    <td class='right'>{f['sold']:,}</td>
                    <td class='right'><b>{f['total']:,}</b></td>
                </tr>
                """
            html += f"""
                <tr class='group-total'>
                    <td colspan='3'><b>GROUP TOTAL</b></td>
                    <td class='right'>{group_total['pcba']:,}</td>
                    <td class='right'>{group_total['material']:,}</td>
                    <td class='right'>{group_total['fix']:,}</td>
                    <td class='right'>{group_total['sold']:,}</td>
                    <td class='right'>{group_total['total']:,}</td>
                </tr>
            </tbody></table>
            """
        html += f"""
        <h3>GRAND TOTAL</h3>
        <table style="width:60%; margin:0 auto;">
            <thead><tr><th>PCBA</th><th>Material</th><th>Fixing</th><th>Soldering</th><th>Total</th></tr></thead>
            <tbody>
                <tr>
                    <td class='right'>{grand['pcba']:,}</td>
                    <td class='right'>{grand['material']:,}</td>
                    <td class='right'>{grand['fixing']:,}</td>
                    <td class='right'>{grand['soldering']:,}</td>
                    <td class='right'>{grand['total']:,}</td>
                </tr>
            </tbody>
        </table>
        <p style="text-align:center; font-size:8pt; margin-top:20px;">Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body></html>"""
        return html

    def _print_html(self, html_content):
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)
            printer.setOrientation(QPrinter.Landscape)
            printer.setPageMargins(8, 8, 8, 8, QPrinter.Millimeter)

            doc = QTextDocument()
            doc.setUseDesignMetrics(True)
            doc.setDocumentMargin(0)
            doc.setDefaultFont(QFont("Segoe UI", 14))
            doc.setHtml(html_content)

            page_rect = printer.pageRect(QPrinter.Point)
            doc.setPageSize(QSizeF(page_rect.width(), page_rect.height()))

            preview = QPrintPreviewDialog(printer, self)
            preview.setWindowState(preview.windowState() | Qt.WindowMaximized)
            preview.setWindowModality(Qt.ApplicationModal)

            def render(printer_obj):
                new_rect = printer_obj.pageRect(QPrinter.Point)
                doc.setPageSize(QSizeF(new_rect.width(), new_rect.height()))
                doc.print_(printer_obj)

            preview.paintRequested.connect(render)
            preview.exec_()
        except Exception as e:
            CustomMessageBox.show_error(self, "Print Error", f"Failed to print: {str(e)}")

    def _print_doc(self, printer, html):
        doc = QTextDocument()
        doc.setDefaultFont(QFont("Segoe UI", 10))
        doc.setDocumentMargin(0)
        doc.setHtml(html)
        doc.setPageSize(QSizeF(printer.paperRect().size()))
        doc.print_(printer)

    def export_rework_report_csv(self):
        self._export_generic("csv", "rework_aggregate", self._get_report_data())

    def export_rework_report_excel(self):
        self._export_generic("excel", "rework_aggregate", self._get_report_data())

    def _get_report_data(self):
        data = []
        for i in range(self.report_layout.count()):
            w = self.report_layout.itemAt(i).widget()
            if isinstance(w, QGroupBox) and "GRAND TOTAL" not in w.title() and "PRODUCTION" not in w.title():
                title = w.title()
                line = re.search(r"LINE:\s*(\S+)", title, re.I); line = line.group(1) if line else ""
                model = re.search(r"MODEL:\s*(\S+)", title, re.I); model = model.group(1) if model else ""
                table = w.findChild(QTableWidget)
                if table:
                    for r in range(table.rowCount()):
                        if table.item(r,0) and table.item(r,0).text() == "TOTAL": continue
                        row_data = [line, model] + [table.item(r,c).text() if table.item(r,c) else "" for c in range(table.columnCount())]
                        data.append(row_data)
        headers = ["Line","Model","Fault Category","Sub Fault","PCBA","Material","Fixing","Soldering","Total"]
        return data, headers

    def _export_generic(self, file_type, base_name, data_and_headers):
        data, headers = data_and_headers
        if not data:
            CustomMessageBox.show_warning(self,"Warning","No data to export")
            return
        ext = "csv" if file_type=="csv" else "xlsx"
        filter_str = f"{file_type.upper()} (*.{ext})"
        fn,_ = QFileDialog.getSaveFileName(self,f"Save {file_type.upper()}", f"{base_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}", filter_str)
        if not fn: return
        try:
            if file_type=="csv":
                with open(fn,'w',newline='',encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(data)
            else:
                pd.DataFrame(data, columns=headers).to_excel(fn, index=False)
            CustomMessageBox.show_success(self,"Success",f"Saved to {os.path.basename(fn)}")
        except Exception as e:
            CustomMessageBox.show_error(self,"Error",str(e))

    # ------------------------------------------------------------------
    # Exports for inspections and rework tables
    # ------------------------------------------------------------------
    def export_csv(self):
        if self.report_table.rowCount()==0: CustomMessageBox.show_warning(self,"Warning","No data to export")
        else:
            fn,_ = QFileDialog.getSaveFileName(self,"Save CSV",f"inspection_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv","CSV (*.csv)")
            if fn:
                data = []
                for row in range(self.report_table.rowCount()):
                    row_data = [self.report_table.item(row,col).text() for col in range(8)]
                    btn = self.report_table.cellWidget(row,8)
                    faults_count = re.findall(r'\d+', btn.text())[0] if btn else "0"
                    row_data.append(faults_count)
                    data.append(row_data)
                with open(fn,'w',newline='',encoding='utf-8-sig') as f:
                    csv.writer(f).writerows([["Date","Time","Station","Model","Employee Name","Employee ID","Line","Floor","Faults"]] + data)
                CustomMessageBox.show_success(self,"Success","Exported.")

    def export_excel(self):
        if not PANDAS_AVAILABLE: CustomMessageBox.show_warning(self,"Warning","pandas not installed")
        elif self.report_table.rowCount()==0: CustomMessageBox.show_warning(self,"Warning","No data")
        else:
            fn,_ = QFileDialog.getSaveFileName(self,"Save Excel",f"inspection_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx","Excel (*.xlsx)")
            if fn:
                data = []
                for row in range(self.report_table.rowCount()):
                    row_data = [self.report_table.item(row,col).text() for col in range(8)]
                    btn = self.report_table.cellWidget(row,8)
                    faults_count = re.findall(r'\d+', btn.text())[0] if btn else "0"
                    row_data.append(faults_count)
                    data.append(row_data)
                df = pd.DataFrame(data, columns=["Date","Time","Station","Model","Employee Name","Employee ID","Line","Floor","Faults"])
                df.to_excel(fn, index=False)
                CustomMessageBox.show_success(self,"Success","Exported.")

    def export_rework_csv(self):
        self._export_rework_generic("csv")

    def export_rework_excel(self):
        self._export_rework_generic("excel")

    def _export_rework_generic(self, typ):
        if self.rework_table.rowCount()==0 or (self.rework_table.rowCount()==1 and "No rework" in self.rework_table.item(0,0).text()):
            CustomMessageBox.show_warning(self,"Warning","No rework data to export")
            return
        fn,_ = QFileDialog.getSaveFileName(self,f"Save {typ.upper()}", f"rework_root_cause_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{typ}", f"{typ.upper()} (*.{typ})")
        if not fn: return
        data = []
        for row in range(self.rework_table.rowCount()):
            if self.rework_table.item(row,0) and "No rework" not in self.rework_table.item(row,0).text():
                data.append([self.rework_table.item(row,col).text() for col in range(10)])
        headers = ["Date","Line","Model","Fault Category","Sub Fault","PCBA","Material","Fixing","Soldering","Total"]
        try:
            if typ=="csv":
                with open(fn,'w',newline='',encoding='utf-8-sig') as f:
                    w = csv.writer(f); w.writerow(headers); w.writerows(data)
            else:
                pd.DataFrame(data, columns=headers).to_excel(fn, index=False)
            CustomMessageBox.show_success(self,"Success","Exported.")
        except Exception as e:
            CustomMessageBox.show_error(self,"Error",str(e))

    # ------------------------------------------------------------------
    # Helpers for line/model/fault options
    # ------------------------------------------------------------------
    def load_line_model_options(self):
        rows = self.db.execute_query("SELECT DISTINCT line, model FROM rework_root_cause WHERE line IS NOT NULL AND line!='' AND model IS NOT NULL AND model!='' ORDER BY line, model", fetch_all=True)
        lines = set()
        self.line_model_map.clear()
        self.all_models = []
        for r in rows:
            lines.add(r['line'])
            self.line_model_map.setdefault(r['line'], []).append(r['model'])
            self.all_models.append(r['model'])
        self.report_line_filter.blockSignals(True)
        self.report_line_filter.clear()
        self.report_line_filter.addItem("All")
        self.report_line_filter.addItems(sorted(lines))
        self.report_line_filter.blockSignals(False)
        self.all_models = sorted(set(self.all_models))
        self.report_model_filter.blockSignals(True)
        self.report_model_filter.clear()
        self.report_model_filter.addItem("All")
        self.report_model_filter.addItems(self.all_models)
        self.report_model_filter.blockSignals(False)

    def on_line_changed(self, line):
        models = self.all_models if line=="All" else self.line_model_map.get(line, [])
        cur = self.report_model_filter.currentText()
        self.report_model_filter.blockSignals(True)
        self.report_model_filter.clear()
        self.report_model_filter.addItem("All")
        self.report_model_filter.addItems(sorted(models))
        idx = self.report_model_filter.findText(cur)
        if idx>=0: self.report_model_filter.setCurrentIndex(idx)
        self.report_model_filter.blockSignals(False)

    def load_fault_categories(self):
        rows = self.db.execute_query("SELECT DISTINCT fault_category FROM rework_root_cause WHERE fault_category IS NOT NULL AND fault_category!='' ORDER BY fault_category", fetch_all=True)
        self.report_fault_filter.clear()
        self.report_fault_filter.addItem("All")
        for r in rows: self.report_fault_filter.addItem(r['fault_category'])

    # ------------------------------------------------------------------
    # Line Summary helpers
    # ------------------------------------------------------------------
    def populate_line_combo(self):
        rows = self.db.execute_query("SELECT DISTINCT LTRIM(RTRIM(line)) as line FROM rework_root_cause WHERE line IS NOT NULL AND line != '' ORDER BY line", fetch_all=True)
        self.summary_line_combo.blockSignals(True)
        self.summary_line_combo.clear()
        self.summary_line_combo.addItem("All Lines")
        for r in rows: self.summary_line_combo.addItem(r['line'])
        self.summary_line_combo.blockSignals(False)

    def on_summary_line_changed(self, line):
        query = "SELECT DISTINCT LTRIM(RTRIM(model)) as model FROM rework_root_cause"
        params = ()
        if line != "All Lines" and line:
            query += " WHERE LTRIM(RTRIM(line)) = ? AND model IS NOT NULL AND model != ''"
            params = (line.strip(),)
        else:
            query += " WHERE model IS NOT NULL AND model != ''"
        rows = self.db.execute_query(query, params, fetch_all=True)
        self.summary_model_combo.blockSignals(True)
        self.summary_model_combo.clear()
        self.summary_model_combo.addItem("All Models")
        for r in rows: self.summary_model_combo.addItem(r['model'])
        self.summary_model_combo.blockSignals(False)

    def populate_fault_categories_summary(self):
        rows = self.db.execute_query("SELECT DISTINCT fault_category FROM rework_root_cause WHERE fault_category IS NOT NULL AND fault_category != '' ORDER BY fault_category", fetch_all=True)
        self.summary_cat_combo.clear()
        self.summary_cat_combo.addItem("All Categories")
        for r in rows: self.summary_cat_combo.addItem(r['fault_category'])

    def on_summary_cat_changed(self, cat):
        if cat == "All Categories" or not cat:
            rows = self.db.execute_query("SELECT DISTINCT fault_subcategory FROM rework_root_cause WHERE fault_subcategory IS NOT NULL AND fault_subcategory != '' ORDER BY fault_subcategory", fetch_all=True)
        else:
            rows = self.db.execute_query("SELECT DISTINCT fault_subcategory FROM rework_root_cause WHERE fault_category=? AND fault_subcategory IS NOT NULL AND fault_subcategory != '' ORDER BY fault_subcategory", (cat,), fetch_all=True)
        self.summary_sub_combo.clear()
        self.summary_sub_combo.addItem("All Sub-Faults")
        for r in rows: self.summary_sub_combo.addItem(r['fault_subcategory'])

    def populate_sub_faults_all(self):
        rows = self.db.execute_query("SELECT DISTINCT fault_subcategory FROM rework_root_cause WHERE fault_subcategory IS NOT NULL AND fault_subcategory != '' ORDER BY fault_subcategory", fetch_all=True)
        self.summary_sub_combo.clear()
        self.summary_sub_combo.addItem("All Sub-Faults")
        for r in rows: self.summary_sub_combo.addItem(r['fault_subcategory'])

    # ------------------------------------------------------------------
    # The following method is kept for compatibility but no longer used.
    # ------------------------------------------------------------------
    def open_root_cause_dialog(self):
        CustomMessageBox.show_info(self, "Info", "Edit Root Cause is now available in the 'Root Cause' tab.")

    def load_resolution_mapping(self):
        rows = self.db.execute_query("""
            SELECT fault_category, fault_subcategory, root_cause, responsible_dept, solution_plan 
            FROM rework_resolution_mapping
        """, fetch_all=True)
        mapping = {}
        for r in rows:
            cat = (r['fault_category'] or '').strip().lower()
            sub = (r['fault_subcategory'] or '').strip().lower()
            key = (cat, sub)
            mapping[key] = {
                'root_cause': r['root_cause'] or '',
                'responsible': r['responsible_dept'] or '',
                'solution': r['solution_plan'] or ''
            }
        return mapping

    def generate_line_rework_summary(self):
        line = self.summary_line_combo.currentText().strip()
        model = self.summary_model_combo.currentText().strip()
        cat = self.summary_cat_combo.currentText().strip()
        sub = self.summary_sub_combo.currentText().strip()
        date_from = self.summary_date_from.date().toString("yyyy-MM-dd")
        date_to = self.summary_date_to.date().toString("yyyy-MM-dd")
        ignore_date = (model != "All Models" and model != "")

        query = """
            SELECT line,
                SUM(pcba_qty) as total_pcba,
                SUM(material_qty) as total_material,
                SUM(fixing_qty) as total_fixing,
                SUM(soldering_qty) as total_soldering,
                SUM(total_qty) as total_rework
            FROM rework_root_cause
            WHERE 1=1
        """
        params = []
        if not ignore_date:
            query += " AND record_date BETWEEN ? AND ?"
            params.extend([date_from, date_to])
        if line and line != "All Lines":
            query += " AND line = ?"
            params.append(line)
        if model and model != "All Models":
            query += " AND model = ?"
            params.append(model)
        if cat and cat != "All Categories":
            query += " AND fault_category = ?"
            params.append(cat)
        if sub and sub != "All Sub-Faults":
            query += " AND fault_subcategory = ?"
            params.append(sub)
        query += " GROUP BY line ORDER BY line"
        rows = self.db.execute_query(query, tuple(params), fetch_all=True)

        if not rows:
            self.summary_output.setHtml("""
            <html><body style="font-family:Arial;padding:20px;">
                <div style="background:#fee2e2; color:#b91c1c; padding:15px; border-radius:8px;">
                    <b>No Data Found</b>
                </div>
            </body></html>""")
            return

        line_totals = {}
        totals = {"pcba": 0, "material": 0, "fixing": 0, "soldering": 0, "total": 0}
        for r in rows:
            ln = r["line"]
            line_totals[ln] = {
                "pcba": r["total_pcba"],
                "material": r["total_material"],
                "fixing": r["total_fixing"],
                "soldering": r["total_soldering"],
                "total": r["total_rework"]
            }
            for k in totals:
                totals[k] += r[f"total_{k}"] if k != "total" else r["total_rework"]

        html = self._render_summary_html(
            totals, line_totals, line, model, cat, sub, ignore_date, date_from, date_to
        )
        self.summary_output.setHtml(html)
        self.summary_output.repaint()

    def _render_summary_html(self, totals, line_totals, line, model, cat, sub,
                            ignore_date, date_from, date_to):
        date_info = f"{date_from} to {date_to}" if not ignore_date else "All dates (model override)"
        html = """<html><head><style>
        body {
            font-family: Arial, sans-serif;
            font-size: 14px;
            margin: 0;
            padding: 10px;
        }
        .title {
            text-align: center;
            font-size: 20px;
            font-weight: bold;
            padding: 12px;
            margin-bottom: 12px;
            background: #111827;
            color: white;
            border-radius: 6px;
        }
        .filters {
            padding: 10px;
            margin-bottom: 12px;
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            font-size: 12px;
            line-height: 1.6;
            border-radius: 4px;
        }
        .section {
            padding: 8px 10px;
            margin-top: 15px;
            margin-bottom: 6px;
            background: #e2e8f0;
            border-left: 5px solid #111827;
            font-size: 16px;
            font-weight: bold;
            border-radius: 3px;
        }
        th {
            background: #111827;
            color: #fff;
            padding: 8px;
            font-size: 13px;
            text-align: center;
        }
        td {
            padding: 6px;
            font-size: 12px;
            vertical-align: top;
        }
        tr:nth-child(even) {
            background: #f9fafb;
        }
        .grand-row td {
            background: #e5e7eb;
            font-weight: bold;
        }
        </style></head><body>"""
        html += "<div class='title'>Rework Summary Report</div>"
        html += f"""
        <div class="filters">
            <b>Line:</b> {line} |
            <b>Model:</b> {model} |
            <b>Category:</b> {cat} |
            <b>Sub:</b> {sub}
            <br>
            <b>Period:</b> {date_info}
        </div>
        """
        if line_totals and line == "All Lines":
            html += "<div class='section'>📊 Per‑Line Totals</div>"
            html += """
            <table width="100%" cellspacing="0" cellpadding="5" style="margin-bottom: 20px;">
                <thead>
                    <tr><th>Line</th><th>PCBA</th><th>Material</th><th>Fixing</th><th>Soldering</th><th>Total</th></tr>
                </thead>
                <tbody>
            """
            for ln in sorted(line_totals.keys()):
                lt = line_totals[ln]
                html += f"""
                <tr>
                    <td><b>{ln}</b></td>
                    <td align="right">{lt['pcba']:,}</td>
                    <td align="right">{lt['material']:,}</td>
                    <td align="right">{lt['fixing']:,}</td>
                    <td align="right">{lt['soldering']:,}</td>
                    <td align="right"><b>{lt['total']:,}</b></td>
                </tr>
                """
            html += f"""
                <tr style="background:#e2e8f0; font-weight:bold;">
                    <td>GRAND TOTAL</td>
                    <td align="right">{totals['pcba']:,}</td>
                    <td align="right">{totals['material']:,}</td>
                    <td align="right">{totals['fixing']:,}</td>
                    <td align="right">{totals['soldering']:,}</td>
                    <td align="right">{totals['total']:,}</td>
                </tr>
                </tbody>
            </table>
            """
        html += "<div class='section'>Total Rework Volume</div>"
        html += '<table width="100%" cellspacing="0" cellpadding="0">'
        html += "<tr><th>Category</th><th>Qty</th><th>%</th></tr>"
        for k in ['pcba', 'material', 'fixing', 'soldering']:
            qty = totals[k]
            pct = (qty / totals['total'] * 100) if totals['total'] else 0
            html += f"""
            <tr>
                <td>{k.upper()}</td>
                <td align="right">{qty:,}</td>
                <td align="right">{pct:.1f}%</td>
            </tr>
            """
        html += f"""
        <tr class="grand-row">
            <td>GRAND TOTAL</td>
            <td align="right">{totals['total']:,}</td>
            <td align="right">100%</td>
        </tr>
        </table>"""
        html += f"""
        <div class="filters" style="margin-top:15px;">
            Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        </body></html>"""
        return html

    def print_line_summary(self):
        html = self.summary_output.toHtml()
        if len(html) < 100:
            CustomMessageBox.show_warning(self, "Warning", "Nothing to print.")
            return
        import re
        html = re.sub(r'@media\s+print\s*\{[^}]*\}', '', html, flags=re.DOTALL)
        html = re.sub(r'@page\s*\{[^}]*\}', '', html, flags=re.DOTALL)
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
        body_content = body_match.group(1) if body_match else html
        print_css = """
        <style>
            @page {
                size: A4 landscape;
                margin: 4mm 3mm;
            }
            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }
            body {
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 6.5pt !important;
                line-height: 1.15;
                margin: 0;
                padding: 0;
                width: 100%;
            }
            .title {
                font-size: 10pt !important;
                font-weight: bold;
                text-align: center;
                margin-bottom: 2px;
                background: #0f172a;
                color: white;
                padding: 2px;
                border-radius: 2px;
            }
            .filters {
                font-size: 5.5pt !important;
                padding: 1px 2px;
                margin-bottom: 2px;
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 2px;
                color: #475569;
            }
            .section {
                font-size: 8pt !important;
                font-weight: bold;
                padding: 1px 2px;
                margin-top: 3px;
                margin-bottom: 1px;
                background: #e2e8f0;
                border-left: 2px solid #0f172a;
            }
            .sub {
                font-size: 6.5pt !important;
                font-weight: bold;
                margin-top: 2px;
                margin-bottom: 1px;
                color: #1e293b;
            }
            table {
                width: 100% !important;
                border-collapse: collapse !important;
                font-size: 5.5pt !important;
                table-layout: fixed !important;
                margin-bottom: 1px;
            }
            th, td {
                border: 1px solid #cbd5e1 !important;
                padding: 1px 1px !important;
                vertical-align: top;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: normal;
                word-break: break-word;
            }
            th {
                background: #1e293b !important;
                color: white !important;
                font-weight: bold;
                text-align: center;
                font-size: 5.5pt !important;
                padding: 2px 1px !important;
            }
            td {
                text-align: left;
            }
            td[align="right"] {
                text-align: right !important;
            }
            th:nth-child(1), td:nth-child(1) { width: 8%; }
            th:nth-child(2), td:nth-child(2) { width: 8%; }
            th:nth-child(3), td:nth-child(3) { width: 5%; }
            th:nth-child(4), td:nth-child(4) { width: 5%; }
            th:nth-child(5), td:nth-child(5) { width: 5%; }
            th:nth-child(6), td:nth-child(6) { width: 5%; }
            th:nth-child(7), td:nth-child(7) { width: 5%; }
            th:nth-child(8), td:nth-child(8) { width: 22%; }
            th:nth-child(9), td:nth-child(9) { width: 10%; }
            th:nth-child(10), td:nth-child(10) { width: 27%; }
            .section + table th:nth-child(1), .section + table td:nth-child(1) { width: 10%; }
            .section + table th:nth-child(2), .section + table td:nth-child(2) { width: 18%; }
            .section + table th:nth-child(3), .section + table td:nth-child(3) { width: 18%; }
            .section + table th:nth-child(4), .section + table td:nth-child(4) { width: 18%; }
            .section + table th:nth-child(5), .section + table td:nth-child(5) { width: 18%; }
            .section + table th:nth-child(6), .section + table td:nth-child(6) { width: 18%; }
            .section + table + table th:nth-child(1), .section + table + table td:nth-child(1) { width: 40%; }
            .section + table + table th:nth-child(2), .section + table + table td:nth-child(2) { width: 30%; }
            .section + table + table th:nth-child(3), .section + table + table td:nth-child(3) { width: 30%; }
            .grand-row td {
                background: #e2e8f0 !important;
                font-weight: bold;
            }
            .filters:last-child {
                font-size: 4.5pt !important;
                text-align: center;
                border: none;
                background: transparent;
                margin-top: 2px;
            }
        </style>
        """
        clean_html = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        {print_css}
    </head>
    <body>
        {body_content}
    </body>
    </html>"""
        self._print_html(clean_html)

    def export_line_summary_html(self):
        html = self.summary_output.toHtml()
        if len(html) < 100:
            CustomMessageBox.show_warning(self, "Warning", "Nothing to export.")
        else:
            fn, _ = QFileDialog.getSaveFileName(
                self,
                "Save HTML",
                f"line_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                "HTML (*.html)"
            )
            if fn:
                with open(fn, 'w', encoding='utf-8') as f:
                    f.write(html)
                CustomMessageBox.show_success(self, "Success", "Saved.")

    # ======================================================================
    # ROOT CAUSE TAB – fully dynamic, date-aware, cascading filters + LOT NO.
    # ======================================================================
    def _get_date_range(self):
        return (self.rc_date_from.date().toString("yyyy-MM-dd"),
                self.rc_date_to.date().toString("yyyy-MM-dd"))

    def setup_root_cause_tab(self):
        layout = QVBoxLayout(self.root_cause_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.rc_total_label = QLabel("")
        self.rc_total_label.setStyleSheet("color: #00e5ff; font-weight: bold; background: rgba(0,0,0,0.3); padding: 5px 12px; border-radius: 20px;")
        layout.addWidget(self._header_frame("🔍 ROOT CAUSE DETAILS (Aggregated by Fault)", self.rc_total_label))

        panel = QFrame()
        panel.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e2e8f0;")
        grid = QGridLayout(panel)
        grid.setContentsMargins(15, 10, 15, 10)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(8)

        self.rc_date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.rc_date_from.setCalendarPopup(True)
        self.rc_date_to = QDateEdit(QDate.currentDate())
        self.rc_date_to.setCalendarPopup(True)

        self.rc_line_combo = QComboBox()
        self.rc_line_combo.addItem("All")
        self.rc_model_combo = QComboBox()
        self.rc_model_combo.addItem("All")
        self.rc_cat_combo = QComboBox()
        self.rc_cat_combo.addItem("All")
        self.rc_sub_combo = QComboBox()
        self.rc_sub_combo.addItem("All")
        self.rc_lot_combo = QComboBox()
        self.rc_lot_combo.addItem("All")

        refresh_btn = self._btn("🔄 Refresh", "#0f2027", self.load_root_cause_data)
        csv_btn = self._btn("📥 CSV", "#28a745", self.export_root_cause_csv)
        if PANDAS_AVAILABLE:
            excel_btn = self._btn("📊 Excel", "#ffc107", self.export_root_cause_excel)
        else:
            excel_btn = None

        edit_btn = self._btn("✏️ Edit Selected", "#1E3A5F", self.edit_selected_root_cause)

        grid.addWidget(QLabel("📅 From:"), 0, 0)
        grid.addWidget(self.rc_date_from, 0, 1)
        grid.addWidget(QLabel("To:"), 0, 2)
        grid.addWidget(self.rc_date_to, 0, 3)
        grid.addWidget(QLabel("Line:"), 1, 0)
        grid.addWidget(self.rc_line_combo, 1, 1)
        grid.addWidget(QLabel("Model:"), 1, 2)
        grid.addWidget(self.rc_model_combo, 1, 3)
        grid.addWidget(QLabel("Fault Category:"), 2, 0)
        grid.addWidget(self.rc_cat_combo, 2, 1)
        grid.addWidget(QLabel("Sub‑Fault:"), 2, 2)
        grid.addWidget(self.rc_sub_combo, 2, 3)
        grid.addWidget(QLabel("Lot No.:"), 3, 0)
        grid.addWidget(self.rc_lot_combo, 3, 1)
        grid.addWidget(refresh_btn, 2, 4, 1, 2)
        grid.addWidget(csv_btn, 0, 4, 1, 1)
        if excel_btn:
            grid.addWidget(excel_btn, 0, 5, 1, 1)
        grid.addWidget(edit_btn, 1, 4, 1, 2)

        layout.addWidget(panel)

        self.rc_table = QTableWidget()
        self.rc_table.setAlternatingRowColors(True)
        self.rc_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                gridline-color: #E2E8F0;
            }
            QHeaderView::section {
                background: #1E3A8A;
                color: white;
                padding: 8px;
                font-weight: bold;
                font-size: 11px;
                border: none;
            }
            QTableWidget::item {
                padding: 6px;
            }
        """)
        self.rc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rc_table.setSortingEnabled(True)
        self.rc_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.rc_table)

        self.rc_table.itemDoubleClicked.connect(self.on_rc_table_double_click)

        self.populate_root_cause_combos()
        self.rc_line_combo.currentTextChanged.connect(self.on_rc_line_changed)
        self.rc_model_combo.currentTextChanged.connect(self.on_rc_model_changed)
        self.rc_cat_combo.currentTextChanged.connect(self.on_rc_cat_changed)
        self.rc_sub_combo.currentTextChanged.connect(self.on_rc_sub_changed)
        self.rc_lot_combo.currentTextChanged.connect(self.load_root_cause_data)
        self.rc_date_from.dateChanged.connect(self.on_rc_date_changed)
        self.rc_date_to.dateChanged.connect(self.on_rc_date_changed)
        
    def populate_root_cause_combos(self):
        date_from, date_to = self._get_date_range()

        rows = self.db.execute_query(
            "SELECT DISTINCT line FROM rework_root_cause WHERE record_date BETWEEN ? AND ? AND line IS NOT NULL AND line != '' ORDER BY line",
            (date_from, date_to),
            fetch_all=True
        )
        self.rc_line_combo.blockSignals(True)
        self.rc_line_combo.clear()
        self.rc_line_combo.addItem("All")
        for r in rows:
            self.rc_line_combo.addItem(r['line'])
        self.rc_line_combo.blockSignals(False)

        self._update_model_combo("All", date_from, date_to)
        self._update_category_combo("All", "All", date_from, date_to)
        self._update_subfault_combo("All", "All", "All", date_from, date_to)
        self._update_lot_combo("All", "All", "All", "All", date_from, date_to)
        self.load_root_cause_data()

    def _update_model_combo(self, line, date_from, date_to):
        if line == "All" or not line:
            query = """
                SELECT DISTINCT model
                FROM rework_root_cause
                WHERE record_date BETWEEN ? AND ?
                  AND model IS NOT NULL AND model != ''
                ORDER BY model
            """
            params = (date_from, date_to)
        else:
            query = """
                SELECT DISTINCT model
                FROM rework_root_cause
                WHERE record_date BETWEEN ? AND ?
                  AND line = ?
                  AND model IS NOT NULL AND model != ''
                ORDER BY model
            """
            params = (date_from, date_to, line)
        rows = self.db.execute_query(query, params, fetch_all=True)
        current = self.rc_model_combo.currentText()
        self.rc_model_combo.blockSignals(True)
        self.rc_model_combo.clear()
        self.rc_model_combo.addItem("All")
        for r in rows:
            self.rc_model_combo.addItem(r['model'])
        idx = self.rc_model_combo.findText(current)
        if idx >= 0:
            self.rc_model_combo.setCurrentIndex(idx)
        self.rc_model_combo.blockSignals(False)

    def _update_category_combo(self, line, model, date_from, date_to):
        query = """
            SELECT DISTINCT fault_category
            FROM rework_root_cause
            WHERE record_date BETWEEN ? AND ?
              AND fault_category IS NOT NULL AND fault_category != ''
        """
        params = [date_from, date_to]
        if line != "All" and line:
            query += " AND line = ?"
            params.append(line)
        if model != "All" and model:
            query += " AND model = ?"
            params.append(model)
        query += " ORDER BY fault_category"
        rows = self.db.execute_query(query, tuple(params), fetch_all=True)
        current = self.rc_cat_combo.currentText()
        self.rc_cat_combo.blockSignals(True)
        self.rc_cat_combo.clear()
        self.rc_cat_combo.addItem("All")
        for r in rows:
            self.rc_cat_combo.addItem(r['fault_category'])
        idx = self.rc_cat_combo.findText(current)
        if idx >= 0:
            self.rc_cat_combo.setCurrentIndex(idx)
        self.rc_cat_combo.blockSignals(False)

    def _update_subfault_combo(self, line, model, category, date_from, date_to):
        query = """
            SELECT DISTINCT fault_subcategory
            FROM rework_root_cause
            WHERE record_date BETWEEN ? AND ?
              AND fault_subcategory IS NOT NULL AND fault_subcategory != ''
        """
        params = [date_from, date_to]
        if line != "All" and line:
            query += " AND line = ?"
            params.append(line)
        if model != "All" and model:
            query += " AND model = ?"
            params.append(model)
        if category != "All" and category:
            query += " AND fault_category = ?"
            params.append(category)
        query += " ORDER BY fault_subcategory"
        rows = self.db.execute_query(query, tuple(params), fetch_all=True)
        current = self.rc_sub_combo.currentText()
        self.rc_sub_combo.blockSignals(True)
        self.rc_sub_combo.clear()
        self.rc_sub_combo.addItem("All")
        for r in rows:
            self.rc_sub_combo.addItem(r['fault_subcategory'])
        idx = self.rc_sub_combo.findText(current)
        if idx >= 0:
            self.rc_sub_combo.setCurrentIndex(idx)
        self.rc_sub_combo.blockSignals(False)

    def _update_lot_combo(self, line, model, category, subfault, date_from, date_to):
        query = """
            SELECT DISTINCT ship_no
            FROM rework_root_cause
            WHERE record_date BETWEEN ? AND ?
              AND ship_no IS NOT NULL AND ship_no != ''
        """
        params = [date_from, date_to]
        if line != "All" and line:
            query += " AND line = ?"
            params.append(line)
        if model != "All" and model:
            query += " AND model = ?"
            params.append(model)
        if category != "All" and category:
            query += " AND fault_category = ?"
            params.append(category)
        if subfault != "All" and subfault:
            query += " AND fault_subcategory = ?"
            params.append(subfault)
        query += " ORDER BY ship_no"
        rows = self.db.execute_query(query, tuple(params), fetch_all=True)
        current = self.rc_lot_combo.currentText()
        self.rc_lot_combo.blockSignals(True)
        self.rc_lot_combo.clear()
        self.rc_lot_combo.addItem("All")
        for r in rows:
            self.rc_lot_combo.addItem(r['ship_no'])
        idx = self.rc_lot_combo.findText(current)
        if idx >= 0:
            self.rc_lot_combo.setCurrentIndex(idx)
        self.rc_lot_combo.blockSignals(False)

    def on_rc_date_changed(self):
        date_from, date_to = self._get_date_range()
        rows = self.db.execute_query(
            "SELECT DISTINCT line FROM rework_root_cause WHERE record_date BETWEEN ? AND ? AND line IS NOT NULL AND line != '' ORDER BY line",
            (date_from, date_to),
            fetch_all=True
        )
        self.rc_line_combo.blockSignals(True)
        self.rc_line_combo.clear()
        self.rc_line_combo.addItem("All")
        for r in rows:
            self.rc_line_combo.addItem(r['line'])
        self.rc_line_combo.blockSignals(False)

        line = self.rc_line_combo.currentText()
        self._update_model_combo(line, date_from, date_to)
        model = self.rc_model_combo.currentText()
        self._update_category_combo(line, model, date_from, date_to)
        category = self.rc_cat_combo.currentText()
        self._update_subfault_combo(line, model, category, date_from, date_to)
        subfault = self.rc_sub_combo.currentText()
        self._update_lot_combo(line, model, category, subfault, date_from, date_to)
        self.load_root_cause_data()

    def on_rc_line_changed(self, line):
        date_from, date_to = self._get_date_range()
        self._update_model_combo(line, date_from, date_to)
        model = self.rc_model_combo.currentText()
        self._update_category_combo(line, model, date_from, date_to)
        category = self.rc_cat_combo.currentText()
        self._update_subfault_combo(line, model, category, date_from, date_to)
        subfault = self.rc_sub_combo.currentText()
        self._update_lot_combo(line, model, category, subfault, date_from, date_to)
        self.load_root_cause_data()

    def on_rc_model_changed(self, model):
        date_from, date_to = self._get_date_range()
        line = self.rc_line_combo.currentText()
        self._update_category_combo(line, model, date_from, date_to)
        category = self.rc_cat_combo.currentText()
        self._update_subfault_combo(line, model, category, date_from, date_to)
        subfault = self.rc_sub_combo.currentText()
        self._update_lot_combo(line, model, category, subfault, date_from, date_to)
        self.load_root_cause_data()

    def on_rc_cat_changed(self, category):
        date_from, date_to = self._get_date_range()
        line = self.rc_line_combo.currentText()
        model = self.rc_model_combo.currentText()
        self._update_subfault_combo(line, model, category, date_from, date_to)
        subfault = self.rc_sub_combo.currentText()
        self._update_lot_combo(line, model, category, subfault, date_from, date_to)
        self.load_root_cause_data()

    def on_rc_sub_changed(self, subfault):
        date_from, date_to = self._get_date_range()
        line = self.rc_line_combo.currentText()
        model = self.rc_model_combo.currentText()
        category = self.rc_cat_combo.currentText()
        self._update_lot_combo(line, model, category, subfault, date_from, date_to)
        self.load_root_cause_data()

    def load_root_cause_data(self):
        date_from = self.rc_date_from.date().toString("yyyy-MM-dd")
        date_to = self.rc_date_to.date().toString("yyyy-MM-dd")
        line = self.rc_line_combo.currentText()
        model = self.rc_model_combo.currentText()
        cat = self.rc_cat_combo.currentText()
        sub = self.rc_sub_combo.currentText()
        lot = self.rc_lot_combo.currentText()

        # Step 1: Aggregate data from rework_root_cause
        query = """
            SELECT
                fault_category,
                fault_subcategory,
                SUM(pcba_qty) AS pcba_qty,
                SUM(material_qty) AS material_qty,
                SUM(fixing_qty) AS fixing_qty,
                SUM(soldering_qty) AS soldering_qty,
                SUM(total_qty) AS total_qty
            FROM rework_root_cause
            WHERE record_date BETWEEN ? AND ?
        """
        params = [date_from, date_to]

        if line != "All":
            query += " AND line = ?"
            params.append(line)
        if model != "All":
            query += " AND model = ?"
            params.append(model)
        if cat != "All":
            query += " AND fault_category = ?"
            params.append(cat)
        if sub != "All":
            query += " AND fault_subcategory = ?"
            params.append(sub)
        if lot != "All":
            query += " AND ship_no = ?"
            params.append(lot)

        query += """
            GROUP BY fault_category, fault_subcategory
            HAVING SUM(total_qty) > 0
            ORDER BY fault_category, fault_subcategory
        """

        rows = self.db.execute_query(query, tuple(params), fetch_all=True)
        self.rc_rows = rows

        # Step 2: Fetch resolution mapping with EXACT MATCH
        # Key: (LOWER(category), LOWER(subcategory)) - exact match only
        mapping_query = """
            SELECT 
                LOWER(LTRIM(RTRIM(fault_category))) as cat,
                LOWER(LTRIM(RTRIM(fault_subcategory))) as sub,
                root_cause,
                responsible_dept,
                solution_plan
            FROM rework_resolution_mapping
        """
        mapping_rows = self.db.execute_query(mapping_query, fetch_all=True)
        
        exact_map = {}
        for m in mapping_rows:
            c = m['cat'] or ''
            s = m['sub'] or ''
            key = (c, s)
            exact_map[key] = {
                'root_cause': m['root_cause'] or '',
                'responsible_dept': m['responsible_dept'] or '',
                'solution_plan': m['solution_plan'] or ''
            }

        # All columns including Root Cause
        headers = [
            "Fault Category", "Sub‑Fault",
            "PCBA", "Material", "Fixing", "Soldering", "Total",
            "Root Cause", "Responsible Dept", "Solution Plan"
        ]
        self.rc_table.setColumnCount(len(headers))
        self.rc_table.setHorizontalHeaderLabels(headers)

        if not rows:
            self.rc_table.setRowCount(1)
            self.rc_table.setSpan(0, 0, 1, len(headers))
            no_item = QTableWidgetItem("No data for selected filters.")
            no_item.setTextAlignment(Qt.AlignCenter)
            self.rc_table.setItem(0, 0, no_item)
            self.rc_total_label.setText("Total Rows: 0")
            return

        self.rc_table.setRowCount(len(rows))
        total_qty = 0
        
        for i, r in enumerate(rows):
            fault_cat = str(r['fault_category'] or '').strip()
            fault_sub = str(r['fault_subcategory'] or '').strip()
            
            # Display: show sub-fault only if it's different from category
            display_sub = fault_sub if fault_sub and fault_sub.upper() != fault_cat.upper() else ""
            
            self.rc_table.setItem(i, 0, QTableWidgetItem(fault_cat))
            self.rc_table.setItem(i, 1, QTableWidgetItem(display_sub))
            
            for col, key in enumerate(['pcba_qty', 'material_qty', 'fixing_qty', 'soldering_qty', 'total_qty'], start=2):
                val = r[key] or 0
                item = QTableWidgetItem(f"{val:,}")
                item.setTextAlignment(Qt.AlignRight)
                self.rc_table.setItem(i, col, item)
                if key == 'total_qty':
                    total_qty += val
            
            # EXACT MATCH for root cause lookup
            cat_lower = fault_cat.lower()
            sub_lower = fault_sub.lower() if fault_sub else ''
            
            mapped = exact_map.get((cat_lower, sub_lower), {
                'root_cause': '',
                'responsible_dept': '',
                'solution_plan': ''
            })
            
            self.rc_table.setItem(i, 7, QTableWidgetItem(mapped['root_cause']))
            self.rc_table.setItem(i, 8, QTableWidgetItem(mapped['responsible_dept']))
            self.rc_table.setItem(i, 9, QTableWidgetItem(mapped['solution_plan']))

        self.rc_table.resizeColumnsToContents()
        self.rc_table.setColumnWidth(0, 180)   # Fault Category
        self.rc_table.setColumnWidth(1, 200)   # Sub-Fault
        self.rc_table.setColumnWidth(7, 250)   # Root Cause
        self.rc_table.setColumnWidth(8, 150)   # Responsible Dept
        self.rc_table.setColumnWidth(9, 250)   # Solution Plan

        self.rc_total_label.setText(f"Total Units: {total_qty:,}  |  Rows: {len(rows)}")
            
    def on_rc_table_double_click(self, item):
        self.edit_selected_root_cause()

    def edit_selected_root_cause(self):
        selected = self.rc_table.currentRow()
        if selected < 0 or selected >= len(self.rc_rows):
            CustomMessageBox.show_warning(self, "Warning", "Please select a row first.")
            return

        row_data = self.rc_rows[selected]
        fault_cat = row_data.get('fault_category', '').strip()
        fault_sub = row_data.get('fault_subcategory', '').strip()

        if not fault_cat:
            CustomMessageBox.show_warning(self, "Warning", "Selected row has no Fault Category.")
            return

        # EXACT MATCH ONLY - no fallback
        cat_lower = fault_cat.lower()
        sub_lower = fault_sub.lower() if fault_sub else ''
        
        existing = {
            'root_cause': '',
            'responsible_dept': '',
            'solution_plan': '',
            'pcba': row_data.get('pcba_qty') or 0,
            'material': row_data.get('material_qty') or 0,
            'fixing': row_data.get('fixing_qty') or 0,
            'soldering': row_data.get('soldering_qty') or 0,
            'total': row_data.get('total_qty') or 0,
        }
        
        # Try exact match only
        exact = self.db.execute_query(
            """SELECT root_cause, responsible_dept, solution_plan 
               FROM rework_resolution_mapping 
               WHERE LOWER(LTRIM(RTRIM(fault_category))) = ? 
               AND LOWER(LTRIM(RTRIM(fault_subcategory))) = ?""",
            (cat_lower, sub_lower),
            fetch_one=True
        )
        if exact:
            existing['root_cause'] = exact['root_cause'] or ''
            existing['responsible_dept'] = exact['responsible_dept'] or ''
            existing['solution_plan'] = exact['solution_plan'] or ''
        # NO FALLBACK - if exact match not found, leave blank

        dlg = RootCauseDialog(self.db, fault_cat, fault_sub, existing, self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_root_cause_data()
            CustomMessageBox.show_success(self, "Success", "Root cause updated.")
            
    def export_root_cause_csv(self):
        self._export_root_cause_generic("csv")

    def export_root_cause_excel(self):
        if not PANDAS_AVAILABLE:
            CustomMessageBox.show_warning(self, "Warning", "pandas not installed.")
            return
        self._export_root_cause_generic("excel")

    def _export_root_cause_generic(self, typ):
        if self.rc_table.rowCount() == 0 or (self.rc_table.rowCount() == 1 and "No data" in self.rc_table.item(0,0).text()):
            CustomMessageBox.show_warning(self, "Warning", "No data to export.")
            return
        fn, _ = QFileDialog.getSaveFileName(
            self,
            f"Save {typ.upper()}",
            f"root_cause_details_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{typ}",
            f"{typ.upper()} (*.{typ})"
        )
        if not fn:
            return

        headers = []
        for col in range(self.rc_table.columnCount()):
            headers.append(self.rc_table.horizontalHeaderItem(col).text())

        data = []
        for row in range(self.rc_table.rowCount()):
            row_data = []
            for col in range(self.rc_table.columnCount()):
                item = self.rc_table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        try:
            if typ == "csv":
                with open(fn, 'w', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f)
                    w.writerow(headers)
                    w.writerows(data)
            else:
                pd.DataFrame(data, columns=headers).to_excel(fn, index=False)
            CustomMessageBox.show_success(self, "Success", f"Exported to {os.path.basename(fn)}")
        except Exception as e:
            CustomMessageBox.show_error(self, "Error", str(e))
            
    # ------------------------------------------------------------------
    # Refresh all
    # ------------------------------------------------------------------
    def refresh(self):
        self.load_inspections()
        self.load_completed_rework()
        self.load_rework_report()