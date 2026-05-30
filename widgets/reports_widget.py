import csv
import re
import os
import datetime
from typing import Dict, List, Optional, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QDateEdit, QComboBox, QGroupBox, QFrame,
    QLineEdit, QHeaderView, QFileDialog, QDialog, QApplication,
    QTabWidget, QScrollArea, QGridLayout, QTextEdit
)
from PyQt5.QtCore import Qt, QDate, QTimer, QSizeF
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5.QtGui import QPageLayout, QPageSize, QColor, QFont, QTextDocument
import html as html_escape

from database import Database
from custom_dialogs import CustomMessageBox

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# ----------------------------------------------------------------------
# FaultDetailsDialog (unchanged)
# ----------------------------------------------------------------------
class FaultDetailsDialog(QDialog):
    def __init__(self, faults_data: Dict[str, int], parent=None):
        super().__init__(parent)
        self.faults_data = faults_data
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Fault Analysis Report")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        self.resize(550, 450)
        self.setWindowFlags(
            Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint | Qt.WindowSystemMenuHint | Qt.WindowStaysOnTopHint
        )
        self.setStyleSheet("background-color: #f5f7fa;")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        self.setLayout(main_layout)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel("🔍")
        icon_label.setStyleSheet("font-size: 24px; background: transparent;")
        header_layout.addWidget(icon_label)

        title_label = QLabel("Fault Breakdown")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        total_faults = sum(self.faults_data.values()) if self.faults_data else 0
        total_badge = QLabel(f"Total: {total_faults}")
        total_badge.setStyleSheet(
            "background-color: #e2e8f0; color: #475569; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(total_badge)
        main_layout.addWidget(header_widget)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #e2e8f0; margin: 5px 0;")
        main_layout.addWidget(sep)

        self.fault_table = QTableWidget()
        self.fault_table.setColumnCount(2)
        self.fault_table.setHorizontalHeaderLabels(["Fault Type", "Quantity"])
        self.fault_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                background: white;
                gridline-color: #f1f5f9;
            }
            QHeaderView::section {
                background: #f8fafc;
                color: #334155;
                padding: 12px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
            }
            QTableWidget::item {
                padding: 10px 12px;
                font-size: 13px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background: #dbeafe;
                color: #1e40af;
            }
        """)
        self.fault_table.horizontalHeader().setStretchLastSection(True)
        self.fault_table.verticalHeader().setVisible(False)
        self.fault_table.setAlternatingRowColors(True)
        self.fault_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.fault_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.fault_table.setColumnWidth(0, 360)
        self.fault_table.setColumnWidth(1, 100)

        if self.faults_data:
            sorted_faults = sorted(self.faults_data.items(), key=lambda x: x[1], reverse=True)
            self.fault_table.setRowCount(len(sorted_faults))
            for row, (fault, qty) in enumerate(sorted_faults):
                fault_item = QTableWidgetItem(fault)
                fault_item.setForeground(QColor("#1e293b"))
                self.fault_table.setItem(row, 0, fault_item)

                qty_item = QTableWidgetItem(str(qty))
                qty_item.setTextAlignment(Qt.AlignCenter)
                if qty >= 30:
                    qty_item.setForeground(QColor("#991b1b"))
                    qty_item.setBackground(QColor("#fee2e2"))
                    qty_item.setFont(QFont("Segoe UI", 11, QFont.Bold))
                elif qty >= 20:
                    qty_item.setForeground(QColor("#9a3412"))
                    qty_item.setBackground(QColor("#ffedd5"))
                    qty_item.setFont(QFont("Segoe UI", 11, QFont.Bold))
                elif qty >= 10:
                    qty_item.setForeground(QColor("#b45309"))
                    qty_item.setBackground(QColor("#fef3c7"))
                    qty_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                elif qty >= 5:
                    qty_item.setForeground(QColor("#d97706"))
                    qty_item.setBackground(QColor("#fffbeb"))
                elif qty > 0:
                    qty_item.setForeground(QColor("#15803d"))
                    qty_item.setBackground(QColor("#dcfce7"))
                else:
                    qty_item.setForeground(QColor("#64748b"))
                    qty_item.setBackground(QColor("#f8fafc"))
                self.fault_table.setItem(row, 1, qty_item)
        else:
            self.fault_table.setRowCount(1)
            no_faults = QTableWidgetItem("✨ No faults recorded for this inspection")
            no_faults.setTextAlignment(Qt.AlignCenter)
            no_faults.setForeground(QColor("#64748b"))
            self.fault_table.setSpan(0, 0, 1, 2)
            self.fault_table.setItem(0, 0, no_faults)

        main_layout.addWidget(self.fault_table)

        button_layout = QHBoxLayout()
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setFixedSize(90, 35)
        copy_btn.setStyleSheet(
            "background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 8px; font-weight: bold; font-size: 12px;")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_btn)
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(100, 35)
        close_btn.setStyleSheet(
            "background: #3b82f6; color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 13px;")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        main_layout.addLayout(button_layout)

        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def copy_to_clipboard(self):
        if not self.faults_data:
            QApplication.clipboard().setText("No faults recorded")
            CustomMessageBox.show_info(self, "Info", "✅ Copied to clipboard!")
            return
        lines = ["FAULT BREAKDOWN", "=" * 50,
                 f"Total Faults: {sum(self.faults_data.values())}",
                 f"Fault Types: {len(self.faults_data)}", "=" * 50, ""]
        for fault, qty in sorted(self.faults_data.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"{fault}: {qty} pcs")
        QApplication.clipboard().setText("\n".join(lines))
        CustomMessageBox.show_info(self, "Success", "✅ Fault data copied to clipboard!")


# ----------------------------------------------------------------------
# ReportsWidget – with 4 tabs (including Line Rework Summary)
# UPDATED: Uses rework_resolution_mapping table for Root Cause/Responsible/Solution
# ----------------------------------------------------------------------
class ReportsWidget(QWidget):
    def __init__(self, db: Database, user_role: str):
        super().__init__()
        self.db = db
        self.user_role = user_role
        self.all_data = []
        self.filtered_data = []
        self.line_model_map = {}
        self.all_models = []
        self.setup_ui()
        self.ensure_tables_exist()
        self.load_inspections()
        self.load_completed_rework()
        self.load_rework_report()

    # ------------------------------------------------------------------
    # Helper to load resolution mapping from database
    # ------------------------------------------------------------------
    def load_resolution_mapping(self):
        """Return dict {fault_category_lowercase: {'root_cause': str, 'responsible': str, 'solution': str}}"""
        mapping = {}
        try:
            rows = self.db.execute_query("""
                SELECT fault_category, root_cause, responsible, solution_plan
                FROM rework_resolution_mapping
                WHERE is_active = 1
            """, fetch_all=True)
            for row in rows:
                cat = row['fault_category'].strip().lower()
                mapping[cat] = {
                    'root_cause': row['root_cause'],
                    'responsible': row['responsible'],
                    'solution': row['solution_plan']
                }
        except Exception as e:
            print(f"Error loading resolution mapping: {e}")
        return mapping

    # ------------------------------------------------------------------
    # Helper to create missing tables (SQL Server)
    # ------------------------------------------------------------------
    def ensure_tables_exist(self):
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_root_cause' AND xtype='U')
                    CREATE TABLE rework_root_cause (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        ship_no NVARCHAR(50),
                        record_date DATE,
                        line NVARCHAR(50),
                        model NVARCHAR(100),
                        fault_category NVARCHAR(100),
                        fault_subcategory NVARCHAR(200),
                        pcba_qty INT DEFAULT 0,
                        material_qty INT DEFAULT 0,
                        fixing_qty INT DEFAULT 0,
                        soldering_qty INT DEFAULT 0,
                        total_qty INT DEFAULT 0,
                        remarks NVARCHAR(MAX),
                        imported_at DATETIME DEFAULT GETDATE()
                    )
                """)
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_completed' AND xtype='U')
                    CREATE TABLE rework_completed (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        line NVARCHAR(50),
                        model NVARCHAR(100),
                        fault_name NVARCHAR(200),
                        source_station NVARCHAR(100),
                        resolved_qty INT,
                        resolution_date DATE,
                        remarks NVARCHAR(MAX),
                        created_at DATETIME DEFAULT GETDATE()
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"Error creating tables: {e}")

    # ------------------------------------------------------------------
    # Main UI – 4 tabs
    # ------------------------------------------------------------------
    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

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
            }
            QTabBar::tab:selected {
                background: #0f2027;
                color: white;
            }
        """)

        self.inspections_tab = QWidget()
        self.setup_inspections_tab()
        self.tab_widget.addTab(self.inspections_tab, "📋 Inspections")

        self.rework_tab = QWidget()
        self.setup_rework_tab()
        self.tab_widget.addTab(self.rework_tab, "✅ Rework Complete")

        self.rework_report_tab = QWidget()
        self.setup_rework_report_tab()
        self.tab_widget.addTab(self.rework_report_tab, "📊 Rework Report")

        self.line_summary_tab = QWidget()
        self.setup_line_rework_summary_tab()
        self.tab_widget.addTab(self.line_summary_tab, "🔧 Line Rework Summary")

        main_layout.addWidget(self.tab_widget)

    # ------------------------------------------------------------------
    # Tab 1: Inspections
    # ------------------------------------------------------------------
    def setup_inspections_tab(self):
        layout = QVBoxLayout(self.inspections_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header_frame = QFrame()
        header_frame.setFixedHeight(50)
        header_frame.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f2027, stop:0.5 #203a43, stop:1 #2c5364); border-radius: 10px;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 0, 20, 0)
        title = QLabel("📊 INSPECTION REPORTS")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.last_updated = QLabel("")
        self.last_updated.setStyleSheet("color: #00b4d8; font-size: 10px;")
        header_layout.addWidget(self.last_updated)
        self.records_count = QLabel("")
        self.records_count.setStyleSheet("color: #00b4d8; font-size: 11px; font-weight: bold;")
        header_layout.addWidget(self.records_count)
        layout.addWidget(header_frame)

        filter_frame = QFrame()
        filter_frame.setFixedHeight(65)
        filter_frame.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #e0e0e0;")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 8, 15, 8)
        filter_layout.setSpacing(12)

        filter_layout.addWidget(QLabel("📅 From:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_from.setCalendarPopup(True)
        self.date_from.setStyleSheet("padding: 5px 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 11px; min-width: 100px;")
        self.date_from.dateChanged.connect(self.generate_inspection_report)
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setStyleSheet("padding: 5px 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 11px; min-width: 100px;")
        self.date_to.dateChanged.connect(self.generate_inspection_report)
        filter_layout.addWidget(self.date_to)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background: #ddd; max-width: 1px;")
        filter_layout.addWidget(sep)

        filter_layout.addWidget(QLabel("🏭 Station:"))
        self.station_filter = QComboBox()
        self.station_filter.addItems(["All", "Semi Test", "MMI Test", "Appearance Test", "Final Test"])
        self.station_filter.setStyleSheet("padding: 5px 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 11px; min-width: 110px;")
        self.station_filter.currentTextChanged.connect(self.generate_inspection_report)
        filter_layout.addWidget(self.station_filter)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("background: #ddd; max-width: 1px;")
        filter_layout.addWidget(sep2)

        filter_layout.addWidget(QLabel("🔎 Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Model, Employee, ID, Fault, Line, Floor...")
        self.search_input.setStyleSheet("padding: 5px 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 11px; min-width: 180px;")
        self.search_input.textChanged.connect(self.generate_inspection_report)
        filter_layout.addWidget(self.search_input)

        filter_layout.addStretch()

        self.generate_btn = QPushButton("🔄 Refresh")
        self.generate_btn.setFixedSize(85, 32)
        self.generate_btn.setStyleSheet(
            "background: #00b4d8; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 11px;")
        self.generate_btn.clicked.connect(self.generate_inspection_report)
        filter_layout.addWidget(self.generate_btn)

        self.export_btn = QPushButton("📥 CSV")
        self.export_btn.setFixedSize(70, 32)
        self.export_btn.setStyleSheet(
            "background: #28a745; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 11px;")
        self.export_btn.clicked.connect(self.export_csv)
        filter_layout.addWidget(self.export_btn)

        if PANDAS_AVAILABLE:
            self.excel_btn = QPushButton("📊 Excel")
            self.excel_btn.setFixedSize(70, 32)
            self.excel_btn.setStyleSheet(
                "background: #ffc107; color: #2d3748; border: none; border-radius: 6px; font-weight: bold; font-size: 11px;")
            self.excel_btn.clicked.connect(self.export_excel)
            filter_layout.addWidget(self.excel_btn)

        layout.addWidget(filter_frame)

        table_frame = QFrame()
        table_frame.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #e0e0e0;")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)

        table_header = QFrame()
        table_header.setFixedHeight(40)
        table_header.setStyleSheet("background: #0f2027; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        header_title_layout = QHBoxLayout(table_header)
        header_title_layout.setContentsMargins(15, 0, 15, 0)
        table_title_label = QLabel("📋 INSPECTION RECORDS")
        table_title_label.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        header_title_layout.addWidget(table_title_label)
        header_title_layout.addStretch()
        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("color: #00b4d8; font-size: 10px;")
        header_title_layout.addWidget(self.loading_label)
        table_layout.addWidget(table_header)

        self.report_table = QTableWidget()
        self.report_table.setColumnCount(9)
        self.report_table.setHorizontalHeaderLabels(
            ["Date", "Time", "Station", "Model", "Employee Name", "Employee ID", "Line", "Floor", "Faults"])
        self.report_table.setAlternatingRowColors(True)
        self.report_table.setStyleSheet("""
            QTableWidget { background: white; border: none; gridline-color: #f0f0f0; }
            QHeaderView::section { background: #1a2a3a; color: white; padding: 8px; font-weight: bold; font-size: 11px; border: none; }
            QTableWidget::item { padding: 8px; font-size: 12px; }
            QTableWidget::item:selected { background: #e3f2fd; }
        """)
        self.report_table.horizontalHeader().setStretchLastSection(True)
        self.report_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.report_table.setSortingEnabled(True)
        self.report_table.setEditTriggers(QTableWidget.NoEditTriggers)
        widths = [90, 70, 110, 150, 130, 90, 70, 80, 0]
        for i, w in enumerate(widths):
            if w > 0:
                self.report_table.setColumnWidth(i, w)
        table_layout.addWidget(self.report_table)
        layout.addWidget(table_frame, 1)

        footer_frame = QFrame()
        footer_frame.setFixedHeight(30)
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(5, 0, 5, 0)
        self.footer_label = QLabel("")
        self.footer_label.setStyleSheet("color: #666; font-size: 10px;")
        footer_layout.addWidget(self.footer_label)
        footer_layout.addStretch()
        self.quick_stats = QLabel("")
        self.quick_stats.setStyleSheet("color: #00b4d8; font-size: 10px; font-weight: bold;")
        footer_layout.addWidget(self.quick_stats)
        layout.addWidget(footer_frame)

        self.report_table.itemDoubleClicked.connect(self.on_row_double_clicked)

    # ------------------------------------------------------------------
    # Tab 2: Rework Complete (Root Cause)
    # ------------------------------------------------------------------
    def setup_rework_tab(self):
        layout = QVBoxLayout(self.rework_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e293b, stop:1 #334155); border-radius: 10px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        title = QLabel("✅ REWORK ROOT CAUSE (Fixed Faults)")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.rework_total_label = QLabel("")
        self.rework_total_label.setStyleSheet("color: #00b4d8; font-size: 11px; font-weight: bold;")
        header_layout.addWidget(self.rework_total_label)
        layout.addWidget(header)

        filter_frame = QFrame()
        filter_frame.setFixedHeight(55)
        filter_frame.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #e0e0e0;")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 5, 15, 5)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("Line:"))
        self.rework_line_filter = QLineEdit()
        self.rework_line_filter.setPlaceholderText("All")
        self.rework_line_filter.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 6px; min-width: 80px;")
        self.rework_line_filter.textChanged.connect(self.load_completed_rework)
        filter_layout.addWidget(self.rework_line_filter)

        filter_layout.addWidget(QLabel("Model:"))
        self.rework_model_filter = QLineEdit()
        self.rework_model_filter.setPlaceholderText("All")
        self.rework_model_filter.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 6px; min-width: 100px;")
        self.rework_model_filter.textChanged.connect(self.load_completed_rework)
        filter_layout.addWidget(self.rework_model_filter)

        filter_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedSize(80, 30)
        refresh_btn.setStyleSheet(
            "background: #00b4d8; color: white; border: none; border-radius: 6px; font-weight: bold;")
        refresh_btn.clicked.connect(self.load_completed_rework)
        filter_layout.addWidget(refresh_btn)

        layout.addWidget(filter_frame)

        self.rework_table = QTableWidget()
        self.rework_table.setAlternatingRowColors(True)
        self.rework_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 8px; }
            QHeaderView::section { background: #334155; color: white; padding: 8px; font-weight: bold; font-size: 11px; }
        """)
        self.rework_table.horizontalHeader().setStretchLastSection(True)
        self.rework_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rework_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.rework_table, 1)

        btn_layout = QHBoxLayout()
        export_csv_btn = QPushButton("📥 Export to CSV")
        export_csv_btn.setFixedSize(120, 35)
        export_csv_btn.setStyleSheet("background: #28a745; color: white; border-radius: 6px; font-weight: bold;")
        export_csv_btn.clicked.connect(self.export_rework_csv)
        btn_layout.addWidget(export_csv_btn)

        if PANDAS_AVAILABLE:
            export_excel_btn = QPushButton("📊 Export to Excel")
            export_excel_btn.setFixedSize(120, 35)
            export_excel_btn.setStyleSheet("background: #ffc107; color: #2d3748; border-radius: 6px; font-weight: bold;")
            export_excel_btn.clicked.connect(self.export_rework_excel)
            btn_layout.addWidget(export_excel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Tab 3: Aggregated Rework Report
    # ------------------------------------------------------------------
    def setup_rework_report_tab(self):
        layout = QVBoxLayout(self.rework_report_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f2027, stop:1 #2c5364); border-radius: 12px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        title = QLabel("📊 REWORK AGGREGATE REPORT")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.report_total_label = QLabel("")
        self.report_total_label.setStyleSheet(
            "color: #00e5ff; font-size: 13px; font-weight: bold; background: rgba(0,0,0,0.3); padding: 5px 12px; border-radius: 20px;")
        header_layout.addWidget(self.report_total_label)
        layout.addWidget(header)

        filter_frame = QFrame()
        filter_frame.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e2e8f0;")
        filter_frame.setFixedHeight(110)
        filter_layout = QGridLayout(filter_frame)
        filter_layout.setContentsMargins(15, 10, 15, 10)
        filter_layout.setHorizontalSpacing(15)
        filter_layout.setVerticalSpacing(8)

        filter_layout.addWidget(QLabel("📅 From:"), 0, 0)
        self.report_date_from = QDateEdit()
        self.report_date_from.setDate(QDate.currentDate().addMonths(-1))
        self.report_date_from.setCalendarPopup(True)
        self.report_date_from.setStyleSheet("padding: 5px; border: 1px solid #cbd5e1; border-radius: 6px;")
        filter_layout.addWidget(self.report_date_from, 0, 1)

        filter_layout.addWidget(QLabel("To:"), 0, 2)
        self.report_date_to = QDateEdit()
        self.report_date_to.setDate(QDate.currentDate())
        self.report_date_to.setCalendarPopup(True)
        self.report_date_to.setStyleSheet("padding: 5px; border: 1px solid #cbd5e1; border-radius: 6px;")
        filter_layout.addWidget(self.report_date_to, 0, 3)

        filter_layout.addWidget(QLabel("Line:"), 1, 0)
        self.report_line_filter = QComboBox()
        self.report_line_filter.addItem("All")
        self.report_line_filter.setStyleSheet("padding: 5px; border: 1px solid #cbd5e1; border-radius: 6px; min-width: 100px;")
        filter_layout.addWidget(self.report_line_filter, 1, 1)

        filter_layout.addWidget(QLabel("Model:"), 1, 2)
        self.report_model_filter = QComboBox()
        self.report_model_filter.addItem("All")
        self.report_model_filter.setStyleSheet("padding: 5px; border: 1px solid #cbd5e1; border-radius: 6px; min-width: 100px;")
        filter_layout.addWidget(self.report_model_filter, 1, 3)

        filter_layout.addWidget(QLabel("Fault Category:"), 1, 4)
        self.report_fault_filter = QComboBox()
        self.report_fault_filter.addItem("All")
        self.report_fault_filter.setStyleSheet("padding: 5px; border: 1px solid #cbd5e1; border-radius: 6px; min-width: 120px;")
        filter_layout.addWidget(self.report_fault_filter, 1, 5)

        refresh_btn = QPushButton("🔄 Generate Report")
        refresh_btn.setStyleSheet(
            "background: #0f2027; color: white; border: none; border-radius: 6px; padding: 5px 15px; font-weight: bold;")
        refresh_btn.clicked.connect(self.load_rework_report)
        filter_layout.addWidget(refresh_btn, 0, 4, 1, 1)

        print_btn = QPushButton("🖨️ Print")
        print_btn.setStyleSheet(
            "background: #475569; color: white; border: none; border-radius: 6px; padding: 5px 15px; font-weight: bold;")
        print_btn.clicked.connect(self.print_rework_report)
        filter_layout.addWidget(print_btn, 0, 5, 1, 1)

        export_csv_btn = QPushButton("📥 CSV")
        export_csv_btn.setStyleSheet(
            "background: #28a745; color: white; border: none; border-radius: 6px; padding: 5px 15px; font-weight: bold;")
        export_csv_btn.clicked.connect(self.export_rework_report_csv)
        filter_layout.addWidget(export_csv_btn, 2, 0, 1, 1)

        if PANDAS_AVAILABLE:
            export_excel_btn = QPushButton("📊 Excel")
            export_excel_btn.setStyleSheet(
                "background: #ffc107; color: #2d3748; border: none; border-radius: 6px; padding: 5px 15px; font-weight: bold;")
            export_excel_btn.clicked.connect(self.export_rework_report_excel)
            filter_layout.addWidget(export_excel_btn, 2, 1, 1, 1)

        layout.addWidget(filter_frame)

        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;")
        self.summary_card.setVisible(False)
        summary_layout = QHBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(15, 10, 15, 10)
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-size: 12px; color: #334155;")
        summary_layout.addWidget(self.summary_label)
        summary_layout.addStretch()
        layout.addWidget(self.summary_card)

        self.report_scroll = QScrollArea()
        self.report_scroll.setWidgetResizable(True)
        self.report_scroll.setStyleSheet("QScrollArea { border: none; background: #f1f5f9; border-radius: 12px; }")
        self.report_container = QWidget()
        self.report_layout = QVBoxLayout(self.report_container)
        self.report_layout.setContentsMargins(15, 15, 15, 15)
        self.report_layout.setSpacing(20)
        self.report_scroll.setWidget(self.report_container)
        layout.addWidget(self.report_scroll)

        self.load_line_model_options()
        self.load_fault_categories()

    # ------------------------------------------------------------------
    # Tab 4: Line Rework Summary (Professional)
    # ------------------------------------------------------------------
    def setup_line_rework_summary_tab(self):
        layout = QVBoxLayout(self.line_summary_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header (unchanged)
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f2027, stop:1 #2c5364); border-radius: 10px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        title = QLabel("🔧 LINE REWORK SUMMARY (Full Breakdown)")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addWidget(header)

        # Filter frame
        filter_frame = QFrame()
        filter_frame.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #e0e0e0;")
        filter_layout = QGridLayout(filter_frame)
        filter_layout.setContentsMargins(15, 10, 15, 10)
        filter_layout.setHorizontalSpacing(15)
        filter_layout.setVerticalSpacing(8)

        # Row 0
        filter_layout.addWidget(QLabel("Line:"), 0, 0)
        self.summary_line_combo = QComboBox()
        self.summary_line_combo.setMinimumWidth(120)
        self.summary_line_combo.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 6px;")
        self.summary_line_combo.currentTextChanged.connect(self.on_summary_line_changed)
        filter_layout.addWidget(self.summary_line_combo, 0, 1)

        filter_layout.addWidget(QLabel("Model:"), 0, 2)
        self.summary_model_combo = QComboBox()
        self.summary_model_combo.setMinimumWidth(120)
        self.summary_model_combo.setEditable(True)
        self.summary_model_combo.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 6px;")
        filter_layout.addWidget(self.summary_model_combo, 0, 3)

        filter_layout.addWidget(QLabel("From:"), 0, 4)
        self.summary_date_from = QDateEdit()
        self.summary_date_from.setDate(QDate.currentDate().addMonths(-1))
        self.summary_date_from.setCalendarPopup(True)
        self.summary_date_from.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 6px;")
        filter_layout.addWidget(self.summary_date_from, 0, 5)

        filter_layout.addWidget(QLabel("To:"), 0, 6)
        self.summary_date_to = QDateEdit()
        self.summary_date_to.setDate(QDate.currentDate())
        self.summary_date_to.setCalendarPopup(True)
        self.summary_date_to.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 6px;")
        filter_layout.addWidget(self.summary_date_to, 0, 7)

        # Row 1
        filter_layout.addWidget(QLabel("Fault Category:"), 1, 0)
        self.summary_cat_combo = QComboBox()
        self.summary_cat_combo.setMinimumWidth(150)
        self.summary_cat_combo.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 6px;")
        self.summary_cat_combo.currentTextChanged.connect(self.on_summary_cat_changed)
        filter_layout.addWidget(self.summary_cat_combo, 1, 1)

        filter_layout.addWidget(QLabel("Sub-Fault:"), 1, 2)
        self.summary_sub_combo = QComboBox()
        self.summary_sub_combo.setMinimumWidth(150)
        self.summary_sub_combo.setEditable(True)
        self.summary_sub_combo.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 6px;")
        filter_layout.addWidget(self.summary_sub_combo, 1, 3)

        # Buttons on row 2 (to avoid column overflow)
        generate_btn = QPushButton("🔄 Generate Report")
        generate_btn.setFixedSize(140, 32)
        generate_btn.setStyleSheet("background: #0f2027; color: white; border-radius: 6px; font-weight: bold;")
        generate_btn.clicked.connect(self.generate_line_rework_summary)
        filter_layout.addWidget(generate_btn, 2, 0, 1, 2)

        export_html_btn = QPushButton("📄 Export HTML")
        export_html_btn.setFixedSize(110, 32)
        export_html_btn.setStyleSheet("background: #6B7280; color: white; border-radius: 6px; font-weight: bold;")
        export_html_btn.clicked.connect(self.export_line_summary_html)
        filter_layout.addWidget(export_html_btn, 2, 2, 1, 2)

        print_btn = QPushButton("🖨️ Print")
        print_btn.setFixedSize(100, 32)
        print_btn.setStyleSheet("background: #1E3A5F; color: white; border-radius: 6px; font-weight: bold;")
        print_btn.clicked.connect(self.print_line_summary)
        filter_layout.addWidget(print_btn, 2, 4, 1, 2)

        filter_layout.setColumnStretch(7, 1)  # stretch last column
        layout.addWidget(filter_frame)

        # Output area (unchanged)
        self.summary_output = QTextEdit()
        self.summary_output.setReadOnly(True)
        self.summary_output.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                font-family: 'Segoe UI';
                font-size: 12px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.summary_output)

        # Populate combos (unchanged)
        self.populate_line_combo()
        self.populate_fault_categories_summary()
        self.populate_sub_faults_all()

    # ------------------------------------------------------------------
    # Helper methods for Tab 4
    # ------------------------------------------------------------------
    def populate_line_combo(self):
        try:
            rows = self.db.execute_query(
                "SELECT DISTINCT LTRIM(RTRIM(line)) as line FROM rework_root_cause WHERE line IS NOT NULL AND line != '' ORDER BY line",
                fetch_all=True
            )
            self.summary_line_combo.blockSignals(True)
            self.summary_line_combo.clear()
            self.summary_line_combo.addItem("All Lines")
            for row in rows:
                self.summary_line_combo.addItem(row['line'])
            self.summary_line_combo.blockSignals(False)
        except Exception as e:
            print(f"Error loading lines: {e}")
            self.summary_line_combo.addItem("All Lines")

    def on_summary_line_changed(self, line):
        try:
            if line == "All Lines" or not line:
                query = """
                    SELECT DISTINCT LTRIM(RTRIM(model)) as model 
                    FROM rework_root_cause 
                    WHERE model IS NOT NULL AND model != '' 
                    ORDER BY model
                """
                params = ()
            else:
                line_clean = line.strip()
                query = """
                    SELECT DISTINCT LTRIM(RTRIM(model)) as model 
                    FROM rework_root_cause 
                    WHERE LTRIM(RTRIM(line)) = ? 
                    AND model IS NOT NULL AND model != '' 
                    ORDER BY model
                """
                params = (line_clean,)
            rows = self.db.execute_query(query, params, fetch_all=True)
            self.summary_model_combo.blockSignals(True)
            self.summary_model_combo.clear()
            self.summary_model_combo.addItem("All Models")
            for row in rows:
                self.summary_model_combo.addItem(row['model'])
            self.summary_model_combo.blockSignals(False)
        except Exception as e:
            print(f"Error loading models: {e}")

    def populate_fault_categories_summary(self):
        try:
            rows = self.db.execute_query(
                "SELECT DISTINCT fault_category FROM rework_root_cause WHERE fault_category IS NOT NULL AND fault_category != '' ORDER BY fault_category",
                fetch_all=True
            )
            self.summary_cat_combo.clear()
            self.summary_cat_combo.addItem("All Categories")
            for row in rows:
                self.summary_cat_combo.addItem(row['fault_category'])
        except Exception as e:
            print(f"Error loading fault categories: {e}")

    def on_summary_cat_changed(self, category):
        try:
            if category == "All Categories" or not category:
                query = "SELECT DISTINCT fault_subcategory FROM rework_root_cause WHERE fault_subcategory IS NOT NULL AND fault_subcategory != '' ORDER BY fault_subcategory"
                params = ()
            else:
                query = "SELECT DISTINCT fault_subcategory FROM rework_root_cause WHERE fault_category = ? AND fault_subcategory IS NOT NULL AND fault_subcategory != '' ORDER BY fault_subcategory"
                params = (category,)
            rows = self.db.execute_query(query, params, fetch_all=True)
            self.summary_sub_combo.clear()
            self.summary_sub_combo.addItem("All Sub-Faults")
            for row in rows:
                self.summary_sub_combo.addItem(row['fault_subcategory'])
        except Exception as e:
            print(f"Error loading sub-faults: {e}")

    def populate_sub_faults_all(self):
        try:
            rows = self.db.execute_query(
                "SELECT DISTINCT fault_subcategory FROM rework_root_cause WHERE fault_subcategory IS NOT NULL AND fault_subcategory != '' ORDER BY fault_subcategory",
                fetch_all=True
            )
            self.summary_sub_combo.clear()
            self.summary_sub_combo.addItem("All Sub-Faults")
            for row in rows:
                self.summary_sub_combo.addItem(row['fault_subcategory'])
        except Exception as e:
            print(f"Error loading sub-faults: {e}")

    def generate_line_rework_summary(self):
        line = self.summary_line_combo.currentText().strip()
        model = self.summary_model_combo.currentText().strip()
        cat = self.summary_cat_combo.currentText().strip()
        sub = self.summary_sub_combo.currentText().strip()
        date_from = self.summary_date_from.date().toString("yyyy-MM-dd")
        date_to = self.summary_date_to.date().toString("yyyy-MM-dd")

        ignore_date = (model != "All Models" and model != "")
        
        query = """
            SELECT 
                line, model, fault_category, fault_subcategory,
                SUM(pcba_qty) as total_pcba,
                SUM(material_qty) as total_material,
                SUM(fixing_qty) as total_fixing,
                SUM(soldering_qty) as total_soldering,
                SUM(total_qty) as total_rework
            FROM rework_root_cause
            WHERE 1=1
        """
        params = []

        if ignore_date:
            pass
        else:
            query += " AND record_date BETWEEN ? AND ?"
            params.append(date_from)
            params.append(date_to)

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

        query += " GROUP BY line, model, fault_category, fault_subcategory ORDER BY line, model, total_rework DESC"

        try:
            rows = self.db.execute_query(query, tuple(params), fetch_all=True)
            if not rows:
                html = f"""
                <html>
                <head><style>
                    body {{ font-family: 'Segoe UI', Arial; margin: 20px; }}
                    .warning {{ color: #dc2626; background: #fee2e2; padding: 15px; border-radius: 8px; }}
                    .info {{ background: #fef9c3; padding: 10px; border-radius: 6px; margin-top: 10px; }}
                    ul {{ margin: 10px 0; padding-left: 20px; }}
                </style></head>
                <body>
                <div class="warning"><b>⚠️ No Data Found for the Selected Filters</b></div>
                <div class="info">
                    <b>Filters applied:</b><br>
                    • Line: {line if line != 'All Lines' else 'All'}<br>
                    • Model: {model if model != 'All Models' else 'All'}<br>
                    • Fault Category: {cat if cat != 'All Categories' else 'All'}<br>
                    • Sub-Fault: {sub if sub != 'All Sub-Faults' else 'All'}<br>
                    • Period: {'All dates (model selected → date ignored)' if ignore_date else f'{date_from} to {date_to}'}
                </div>
                <div class="info">
                    <b>Possible reasons:</b>
                    <ul>
                        <li>No rework records exist for the selected combination.</li>
                        <li>The model may not have run on this line during the period (if date filter was active).</li>
                        <li>Try a different line, model, or fault category.</li>
                    </ul>
                </div>
                </body></html>
                """
                self.summary_output.setHtml(html)
                return

            # NEW: Use mapping from rework_resolution_mapping table
            mapping_dict = self.load_resolution_mapping()

            lines_data = {}
            for row in rows:
                line_name = row['line']
                if line_name not in lines_data:
                    lines_data[line_name] = {}
                model_name = row['model']
                if model_name not in lines_data[line_name]:
                    lines_data[line_name][model_name] = []
                lines_data[line_name][model_name].append(row)

            cat_totals = {}
            for row in rows:
                fc = row['fault_category']
                cat_totals[fc] = cat_totals.get(fc, 0) + row['total_rework']
            sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
            top_weak = sorted_cats[:3]

            total_pcba = sum(r['total_pcba'] for r in rows)
            total_material = sum(r['total_material'] for r in rows)
            total_fixing = sum(r['total_fixing'] for r in rows)
            total_soldering = sum(r['total_soldering'] for r in rows)
            total_all = sum(r['total_rework'] for r in rows)

            date_info = f"{date_from} to {date_to}" if not ignore_date else "All dates (model selected → date range ignored)"

            html = f"""
            <html>
            <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial; margin: 20px; }}
                h2 {{ color: #0f2027; border-bottom: 2px solid #0f2027; padding-bottom: 5px; }}
                h3 {{ color: #2c5364; margin-top: 20px; }}
                h4 {{ background: #e9ecef; padding: 5px 10px; border-radius: 6px; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 12px; }}
                th, td {{ border: 1px solid #cbd5e1; padding: 8px 8px; text-align: left; vertical-align: top; }}
                th {{ background: #1e293b; color: white; }}
                .totals-table td {{ text-align: right; }}
                .note {{ font-style: italic; color: #6c757d; margin-top: 10px; }}
            </style>
            </head>
            <body>
            <h2>🔧 Rework Summary Report</h2>
            <p><b>Filters:</b> Line: {line if line != 'All Lines' else 'All'} | Model: {model if model != 'All Models' else 'All'} | Fault Category: {cat if cat != 'All Categories' else 'All'} | Sub-Fault: {sub if sub != 'All Sub-Faults' else 'All'}</p>
            <p><b>Period:</b> {date_info}</p>
            """

            if ignore_date:
                html += "<p class='note'>ℹ️ Note: Because a specific model was selected, the date range was ignored and all available dates are shown.</p>"

            html += f"""
            <h3>📊 Total Rework Volume</h3>
            <table class="totals-table">
            <tr><th>Category</th><th>Quantity</th><th>% of Total</th></tr>
            <tr><td style="text-align:right;">PCBA</td><td style="text-align:right;">{total_pcba:,}</td><td style="text-align:right;">{total_pcba/total_all*100:.1f}%</td></tr>
            <tr><td style="text-align:right;">Material</td><td style="text-align:right;">{total_material:,}</td><td style="text-align:right;">{total_material/total_all*100:.1f}%</td></tr>
            <tr><td style="text-align:right;">Fixing</td><td style="text-align:right;">{total_fixing:,}</td><td style="text-align:right;">{total_fixing/total_all*100:.1f}%</td></tr>
            <tr><td style="text-align:right;">Soldering</td><td style="text-align:right;">{total_soldering:,}</td><td style="text-align:right;">{total_soldering/total_all*100:.1f}%</td></tr>
            <tr style="font-weight:bold; background:#f1f5f9;"><td style="text-align:right;">GRAND TOTAL</td><td style="text-align:right;">{total_all:,}</td><td style="text-align:right;">100%</td></tr>
            </table>
            """

            html += "<h3>🔧 Detailed Breakdown by Line, Model, Fault Category & Sub-Fault</h3>"
            for line_name, models in lines_data.items():
                html += f"<h3>Line: {line_name}</h3>"
                for model_name, faults in models.items():
                    html += f"<h4>Model: {model_name}</h4>"
                    html += """
                    <table>
                    <thead>
                    <tr><th>Fault Category</th><th>Sub-Fault</th><th>PCBA</th><th>Material</th><th>Fixing</th><th>Soldering</th><th>Total</th><th>Root Cause</th><th>Responsible</th><th>Solution Plan</th></tr>
                    </thead><tbody>
                    """
                    for f in faults:
                        fc = f['fault_category']
                        subf = f['fault_subcategory'] or "-"
                        pcba = f['total_pcba']
                        mat = f['total_material']
                        fix = f['total_fixing']
                        sold = f['total_soldering']
                        tot = f['total_rework']
                        fc_lower = fc.strip().lower()
                        map_info = mapping_dict.get(fc_lower, {})
                        root = map_info.get('root_cause', 'Not defined')
                        dept = map_info.get('responsible', 'N/A')
                        soln = map_info.get('solution', 'No solution')
                        html += f"""
                        <tr>
                            <td>{fc}</td><td>{subf}</td>
                            <td style="text-align:right;">{pcba:,}</td>
                            <td style="text-align:right;">{mat:,}</td>
                            <td style="text-align:right;">{fix:,}</td>
                            <td style="text-align:right;">{sold:,}</td>
                            <td style="text-align:right;"><b>{tot:,}</b></td>
                            <td>{root}</td><td>{dept}</td><td>{soln}</td>
                        </tr>
                        """
                    html += "</tbody></table><br>"

            html += "<h3>⚠️ Top Weak Points (based on rework volume)</h3><ul>"
            for fc, qty in top_weak:
                fc_lower = fc.strip().lower()
                map_info = mapping_dict.get(fc_lower, {})
                root = map_info.get('root_cause', 'Unknown')
                soln = map_info.get('solution', 'Investigate')
                html += f"<li><b>{fc}</b> – {qty:,} units rework.<br>Root cause: {root}<br>Recommended action: {soln}</li>"
            html += "</ul>"

            html += """
            <p style="font-size:11px; color:gray;">SSH FACTORY Report generated on {}</p>
            </body></html>
            """.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            self.summary_output.setHtml(html)

        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Failed to generate report: {str(e)}")

    def print_line_summary(self):
        """Print the current line rework summary (HTML content) with proper layout"""
        html = self.summary_output.toHtml()
        if not html or len(html) < 100:
            CustomMessageBox.show_warning(self, "Warning", "No summary to print. Please generate first.")
            return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Landscape)

        # Set minimal margins (5mm) to maximize printable area
        from PyQt5.QtCore import QMarginsF
        page_layout = printer.pageLayout()
        page_layout.setUnits(QPageLayout.Millimeter)
        page_layout.setMargins(QMarginsF(5, 5, 5, 5))
        printer.setPageLayout(page_layout)

        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(lambda p: self._print_html(p, html))
        preview.exec_()  
            
    def export_line_summary_html(self):
        """Export the current line rework summary to an HTML file"""
        html = self.summary_output.toHtml()
        if not html or len(html) < 100:
            CustomMessageBox.show_warning(self, "Warning", "No summary to export. Please generate first.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save HTML Report",
                                                f"line_rework_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                                                "HTML (*.html)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html)
                CustomMessageBox.show_success(self, "Success", f"Report saved to {os.path.basename(filename)}")
            except Exception as e:
                CustomMessageBox.show_error(self, "Error", f"Failed to save: {str(e)}")

    def _print_html(self, printer, html):
        """Print HTML content with proper scaling to fill the page"""
        from PyQt5.QtCore import QSizeF
        from PyQt5.QtGui import QTextDocument, QFont

        doc = QTextDocument()
        doc.setDefaultFont(QFont("Segoe UI", 10))

        # Enhanced print CSS for full page usage
        print_style = """
        <style>
            @media print {
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                body {
                    margin: 0;
                    padding: 5px;
                    width: 100%;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 10pt;
                    background: white;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    page-break-inside: avoid;
                }
                th, td {
                    border: 1px solid #888;
                    padding: 6px 5px;
                    text-align: left;
                    vertical-align: top;
                    font-size: 9pt;
                }
                th {
                    background: #e2e8f0;
                    font-weight: bold;
                }
                .totals-table td {
                    text-align: right;
                }
                h2, h3, h4 {
                    page-break-after: avoid;
                    margin-top: 8px;
                    margin-bottom: 5px;
                }
                .note {
                    font-size: 8pt;
                    color: #666;
                }
            }
        </style>
        """
        # Inject print CSS into HTML
        if '<head>' in html:
            html = html.replace('<head>', '<head>' + print_style)
        else:
            html = '<html><head>' + print_style + '</head><body>' + html + '</body></html>'

        doc.setHtml(html)

        # Use the printer's actual printable area size
        page_rect = printer.pageRect()
        page_size = QSizeF(page_rect.size())
        doc.setPageSize(page_size)
        doc.setDocumentMargin(0)   # remove internal margins

        doc.print_(printer)
    # ------------------------------------------------------------------
    # Existing data loading methods (unchanged, but method names corrected)
    # ------------------------------------------------------------------
    def load_inspections(self):
        self.loading_label.setText("🔄 Loading...")
        QApplication.processEvents()
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        inspection_code,
                        inspection_date,
                        inspection_type,
                        defects,
                        remarks,
                        rejected_quantity,
                        line,
                        floor
                    FROM inspections 
                    WHERE product_id IS NULL OR inspection_type IN ('MMI Test', 'Semi Test', 'Appearance Test', 'Final Test')
                    ORDER BY inspection_date DESC
                """)
                rows = cursor.fetchall()
                self.all_data = []
                for row in rows:
                    remarks = row[4] if row[4] else ""
                    defects_text = row[3] if row[3] else ""
                    faults = self.parse_faults_from_defects(defects_text)
                    recalc_total = sum(faults.values()) if faults else 0
                    rejected_qty = row[5] if row[5] else 0
                    defects_count = recalc_total if recalc_total > 0 else rejected_qty
                    if rejected_qty > 0 and not faults:
                        faults["Total Faults"] = rejected_qty
                        defects_count = rejected_qty

                    model = self.extract_value(remarks, "Model:") or "N/A"
                    employee = self.extract_value(remarks, "Employee:") or "N/A"
                    employee_id = self.extract_value(remarks, "Employee ID:") or self.extract_value(remarks, "Tester ID:") or "N/A"
                    line = row[6] if row[6] else "N/A"
                    floor = row[7] if row[7] else "N/A"

                    inspection_date = row[1] if row[1] else datetime.datetime.now()
                    self.all_data.append({
                        'date': inspection_date.strftime('%Y-%m-%d') if hasattr(inspection_date, 'strftime') else str(inspection_date)[:10],
                        'time': inspection_date.strftime('%H:%M:%S') if hasattr(inspection_date, 'strftime') else '',
                        'station': row[2] if row[2] else 'MMI Test',
                        'model': model,
                        'employee': employee,
                        'employee_id': employee_id,
                        'line': line,
                        'floor': floor,
                        'defects_count': defects_count,
                        'faults': faults,
                        'inspection_code': row[0] if row[0] else ''
                    })
                self.generate_inspection_report()
                self.last_updated.setText(f"Updated: {datetime.datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"Error loading inspections: {e}")
            import traceback
            traceback.print_exc()
            self.all_data = []
            self.generate_inspection_report()
        self.loading_label.setText("✅ Ready")
        QTimer.singleShot(1500, lambda: self.loading_label.setText(""))

    def load_completed_rework(self):
        try:
            line_filter = self.rework_line_filter.text().strip()
            model_filter = self.rework_model_filter.text().strip()

            query = """
                SELECT 
                    line, model, fault_category, fault_subcategory,
                    pcba_qty, material_qty, fixing_qty, soldering_qty, total_qty,
                    record_date
                FROM rework_root_cause
                WHERE 1=1
            """
            params = []
            if line_filter:
                query += " AND line LIKE ?"
                params.append(f"%{line_filter}%")
            if model_filter:
                query += " AND model LIKE ?"
                params.append(f"%{model_filter}%")
            query += " ORDER BY record_date DESC, imported_at DESC"

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                records = [dict(zip(columns, row)) for row in rows]

            self.rework_table.clear()
            self.rework_table.setRowCount(0)

            new_headers = ["Date", "Line", "Model", "Fault Category", "Sub Fault",
                           "PCBA", "Material", "Fixing", "Soldering", "Total"]
            self.rework_table.setColumnCount(len(new_headers))
            self.rework_table.setHorizontalHeaderLabels(new_headers)

            if not records:
                self.rework_table.setRowCount(1)
                no_data = QTableWidgetItem("No rework root cause data found. Import via ReworkWidget.")
                no_data.setTextAlignment(Qt.AlignCenter)
                self.rework_table.setSpan(0, 0, 1, len(new_headers))
                self.rework_table.setItem(0, 0, no_data)
                self.rework_total_label.setText("Total Units: 0")
                return

            self.rework_table.setRowCount(len(records))
            total_units = 0
            for row, rec in enumerate(records):
                date_val = rec.get('record_date', '')
                if hasattr(date_val, 'strftime'):
                    date_val = date_val.strftime('%Y-%m-%d')
                date_item = QTableWidgetItem(str(date_val))
                date_item.setTextAlignment(Qt.AlignCenter)
                self.rework_table.setItem(row, 0, date_item)

                self.rework_table.setItem(row, 1, QTableWidgetItem(str(rec.get('line', 'N/A'))))
                self.rework_table.setItem(row, 2, QTableWidgetItem(str(rec.get('model', 'N/A'))))
                self.rework_table.setItem(row, 3, QTableWidgetItem(str(rec.get('fault_category', ''))))
                self.rework_table.setItem(row, 4, QTableWidgetItem(str(rec.get('fault_subcategory', ''))))

                for col_idx, key in enumerate(['pcba_qty', 'material_qty', 'fixing_qty', 'soldering_qty', 'total_qty'], start=5):
                    val = rec.get(key, 0)
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.rework_table.setItem(row, col_idx, item)

                total_units += rec.get('total_qty', 0)

            self.rework_total_label.setText(f"Total Units: {total_units}")
            widths = [90, 80, 100, 150, 150, 60, 60, 60, 60, 70]
            for i, width in enumerate(widths):
                self.rework_table.setColumnWidth(i, width)
            self.rework_table.viewport().update()
            self.rework_table.update()
        except Exception as e:
            print(f"Error loading rework root cause data: {e}")
            import traceback
            traceback.print_exc()
            self.rework_table.clear()
            self.rework_table.setRowCount(1)
            error_item = QTableWidgetItem(f"Error: {str(e)}")
            error_item.setTextAlignment(Qt.AlignCenter)
            self.rework_table.setSpan(0, 0, 1, 10)
            self.rework_table.setItem(0, 0, error_item)

    def load_rework_report(self):
        for i in reversed(range(self.report_layout.count())):
            w = self.report_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        date_from = self.report_date_from.date().toString("yyyy-MM-dd")
        date_to = self.report_date_to.date().toString("yyyy-MM-dd")
        line_filter = self.report_line_filter.currentText()
        model_filter = self.report_model_filter.currentText()
        fault_filter = self.report_fault_filter.currentText()

        try:
            query = """
                SELECT 
                    line, model, fault_category, fault_subcategory,
                    pcba_qty, material_qty, fixing_qty, soldering_qty, total_qty
                FROM rework_root_cause
                WHERE record_date BETWEEN ? AND ?
            """
            params = [date_from, date_to]
            if line_filter != "All":
                query += " AND line = ?"
                params.append(line_filter)
            if model_filter != "All":
                query += " AND model = ?"
                params.append(model_filter)
            if fault_filter != "All":
                query += " AND fault_category = ?"
                params.append(fault_filter)
            query += " ORDER BY line, model, fault_category, fault_subcategory"

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

            if not rows:
                no_data = QLabel("⚠️ No rework data found for the selected filters.\nPlease change the date range or filter criteria.")
                no_data.setAlignment(Qt.AlignCenter)
                no_data.setStyleSheet("font-size: 14px; color: #64748b; padding: 50px; background: white; border-radius: 12px;")
                self.report_layout.addWidget(no_data)
                self.report_total_label.setText("Total: 0 units")
                self.summary_card.setVisible(False)
                return

            groups = {}
            for row in rows:
                line, model, fault_cat, fault_sub, pcba, material, fixing, soldering, total = row
                key = (line, model)
                groups.setdefault(key, []).append({
                    'fault_category': fault_cat or "General",
                    'fault_subcategory': fault_sub or "",
                    'pcba': pcba or 0,
                    'material': material or 0,
                    'fixing': fixing or 0,
                    'soldering': soldering or 0,
                    'total': total or 0
                })

            grand_totals = {'pcba': 0, 'material': 0, 'fixing': 0, 'soldering': 0, 'total': 0}
            group_count = 0

            for (line, model), faults in groups.items():
                QApplication.processEvents()
                group_count += 1
                group_box = QGroupBox(f"  LINE: {line}  |  MODEL: {model}  ")
                group_box.setStyleSheet("""
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
                group_layout = QVBoxLayout(group_box)
                group_layout.setContentsMargins(5, 10, 5, 5)

                table = QTableWidget()
                table.setColumnCount(7)
                table.setHorizontalHeaderLabels(["Fault Category", "Sub Fault", "PCBA", "Material", "Fixing", "Soldering", "Total"])
                table.setAlternatingRowColors(True)
                table.setStyleSheet("""
                    QTableWidget {
                        border: 1px solid #cbd5e1;
                        background: white;
                        border-radius: 6px;
                        gridline-color: #e2e8f0;
                    }
                    QHeaderView::section {
                        background: #334155;
                        color: white;
                        padding: 6px;
                        font-weight: bold;
                        font-size: 11px;
                        border: none;
                    }
                    QTableWidget::item {
                        padding: 4px;
                        font-size: 11px;
                    }
                """)
                table.horizontalHeader().setStretchLastSection(True)
                table.setEditTriggers(QTableWidget.NoEditTriggers)

                faults_sorted = sorted(faults, key=lambda x: x['fault_category'])
                table.setRowCount(len(faults_sorted))

                row_totals = {'pcba': 0, 'material': 0, 'fixing': 0, 'soldering': 0, 'total': 0}
                for i, f in enumerate(faults_sorted):
                    QApplication.processEvents()
                    table.setItem(i, 0, QTableWidgetItem(f['fault_category']))
                    table.setItem(i, 1, QTableWidgetItem(f['fault_subcategory']))
                    for col, key in enumerate(['pcba', 'material', 'fixing', 'soldering', 'total'], start=2):
                        val = f[key]
                        item = QTableWidgetItem(f"{val:,}")
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        table.setItem(i, col, item)
                        row_totals[key] += val
                        grand_totals[key] += val

                table.setRowCount(len(faults_sorted) + 1)
                total_label = QTableWidgetItem("TOTAL")
                total_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
                total_label.setBackground(QColor("#f1f5f9"))
                table.setItem(len(faults_sorted), 0, total_label)
                table.setSpan(len(faults_sorted), 0, 1, 2)
                for col, key in enumerate(['pcba', 'material', 'fixing', 'soldering', 'total'], start=2):
                    total_item = QTableWidgetItem(f"{row_totals[key]:,}")
                    total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    total_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                    total_item.setBackground(QColor("#f1f5f9"))
                    table.setItem(len(faults_sorted), col, total_item)

                table.resizeColumnsToContents()
                table.setColumnWidth(0, 140)
                table.setColumnWidth(1, 140)
                group_layout.addWidget(table)
                self.report_layout.addWidget(group_box)

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
            grand_table.setHorizontalHeaderLabels(["Metric", "PCBA", "Material", "Fixing", "Soldering", "Total"])
            grand_table.setRowCount(1)
            grand_table.setItem(0, 0, QTableWidgetItem("All Faults"))
            for col, key in enumerate(['pcba', 'material', 'fixing', 'soldering', 'total'], start=1):
                item = QTableWidgetItem(f"{grand_totals[key]:,}")
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item.setFont(QFont("Segoe UI", 11, QFont.Bold))
                grand_table.setItem(0, col, item)
            grand_table.resizeColumnsToContents()
            grand_table.setEditTriggers(QTableWidget.NoEditTriggers)
            grand_layout.addWidget(grand_table)
            self.report_layout.addWidget(grand_box)

            output_box = QGroupBox("PRODUCTION OUTPUT")
            output_box.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    font-size: 13px;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    margin-top: 10px;
                }
                QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 10px; }
            """)
            output_layout = QVBoxLayout(output_box)
            output_table = QTableWidget()
            output_table.setColumnCount(3)
            output_table.setHorizontalHeaderLabels(["Line", "Output", "Model"])
            output_table.setRowCount(0)
            output_table.setStyleSheet("border: none;")
            output_layout.addWidget(output_table)
            output_label = QLabel("* Production output data can be imported from CSV.")
            output_label.setStyleSheet("padding: 5px; color: #64748b; font-size: 10px;")
            output_layout.addWidget(output_label)
            self.report_layout.addWidget(output_box)

            total_units = grand_totals['total']
            self.report_total_label.setText(f"Total: {total_units:,} units")
            filter_text = f"Line: {line_filter if line_filter != 'All' else 'All'} | Model: {model_filter if model_filter != 'All' else 'All'} | Fault: {fault_filter if fault_filter != 'All' else 'All'}"
            self.summary_label.setText(f"📋 {group_count} group(s) | Filters: {filter_text} | Period: {date_from} to {date_to}")
            self.summary_card.setVisible(True)

        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Failed to load rework report: {str(e)}")

    # ------------------------------------------------------------------
    # Print and export methods
    # ------------------------------------------------------------------
    def print_rework_report(self):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Landscape)
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(self._print_report_content)
        preview.exec_()

    def _print_report_content(self, printer):
        from PyQt5.QtCore import QSizeF
        from PyQt5.QtGui import QTextDocument, QFont
        import html as html_escape
        import datetime

        date_from = self.report_date_from.date().toString("yyyy-MM-dd")
        date_to = self.report_date_to.date().toString("yyyy-MM-dd")
        line_filter = html_escape.escape(self.report_line_filter.currentText())
        model_filter = html_escape.escape(self.report_model_filter.currentText())
        fault_filter = html_escape.escape(self.report_fault_filter.currentText())

        query = """
            SELECT
                record_date,
                line,
                model,
                fault_category,
                fault_subcategory,
                pcba_qty,
                material_qty,
                fixing_qty,
                soldering_qty,
                total_qty
            FROM rework_root_cause
            WHERE record_date BETWEEN ? AND ?
        """
        params = [date_from, date_to]
        if line_filter != "All":
            query += " AND line = ?"
            params.append(line_filter)
        if model_filter != "All":
            query += " AND model = ?"
            params.append(model_filter)
        if fault_filter != "All":
            query += " AND fault_category = ?"
            params.append(fault_filter)
        query += " ORDER BY line, model, record_date, fault_category"

        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, params)
                rows = cur.fetchall()
        except Exception as e:
            doc = QTextDocument()
            doc.setPlainText(f"Database Error:\n{str(e)}")
            doc.print_(printer)
            return

        if not rows:
            doc = QTextDocument()
            doc.setPlainText("No data found.")
            doc.print_(printer)
            return

        groups = {}
        for row in rows:
            date_val = row[0]
            date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)[:10]
            line = row[1] or "N/A"
            model = row[2] or "N/A"
            cat = row[3] or ""
            sub = row[4] or ""
            pcba = row[5] or 0
            mat = row[6] or 0
            fix = row[7] or 0
            sold = row[8] or 0
            total = row[9] or 0
            key = (line, model)
            groups.setdefault(key, []).append({
                "date": date_str, "cat": cat, "sub": sub,
                "pcba": pcba, "mat": mat, "fix": fix, "sold": sold, "total": total
            })

        grand = {"pcba": 0, "mat": 0, "fix": 0, "sold": 0, "total": 0}
        for faults in groups.values():
            for f in faults:
                grand["pcba"] += f["pcba"]
                grand["mat"] += f["mat"]
                grand["fix"] += f["fix"]
                grand["sold"] += f["sold"]
                grand["total"] += f["total"]

        css = """
        body{ font-family: Arial; font-size: 10pt; margin:0; padding:0; color:#222; }
        table{ width:100%; border-collapse:collapse; table-layout:fixed; }
        th, td{ border:1px solid #d0d7e5; padding:5px; font-size:9pt; white-space:nowrap; overflow:hidden; }
        th{ background:#d9e2f3; text-align:center; font-weight:bold; }
        .left{ text-align:left; }
        .right{ text-align:right; }
        .date{ width:100px; text-align:center; white-space:nowrap; }
        .group-header{ background:#1f4e78; color:white; padding:8px; font-weight:bold; }
        .group-total{ background:#fff2cc; font-weight:bold; }
        .grand-title{ background:#1f4e78; color:white; text-align:center; padding:10px; font-weight:bold; }
        .group-meta{ width:100%; border-collapse:collapse; table-layout:fixed; margin-top:10px; }
        .group-meta td{ border:1px solid #2f5597; padding:5px; font-size:9pt; box-sizing:border-box; }
        .g-label{ width:70px; background:#2f5597; color:white; font-weight:bold; text-align:center; }
        .g-value{ background:#eef3fb; font-weight:bold; text-align:left; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        """

        html = f"""
        <html>
        <head><style>{css}</style></head>
        <body>
        <div class="group-header" style="text-align:center;">SSH FACTORY - REWORK REPORT<br><small>{date_from} TO {date_to}</small></div>
        """
        for (line, model), fault_list in groups.items():
            html += f"""
            <div style="margin-top:15px;">
            <table class="group-meta"><tr><td class="g-label">LINE</td><td class="g-value">{line}</td><td class="g-label">MODEL</td><td class="g-value">{model}</td></tr></table>
            <table><thead><tr><th class="date">Date</th><th>Fault Category</th><th>Sub Fault</th><th>PCBA</th><th>Material</th><th>Fixing</th><th>Soldering</th><th>Total</th></tr></thead><tbody>
            """
            group_total = {"pcba":0,"mat":0,"fix":0,"sold":0,"total":0}
            for f in fault_list:
                group_total["pcba"] += f["pcba"]
                group_total["mat"] += f["mat"]
                group_total["fix"] += f["fix"]
                group_total["sold"] += f["sold"]
                group_total["total"] += f["total"]
                html += f"""
                <tr><td class="date">{f['date']}</td><td class="left">{f['cat']}</td><td class="left">{f['sub']}</td>
                <td class="right">{f['pcba']:,}</td><td class="right">{f['mat']:,}</td><td class="right">{f['fix']:,}</td>
                <td class="right">{f['sold']:,}</td><td class="right"><b>{f['total']:,}</b></td></tr>
                """
            html += f"""
            <tr class="group-total"><td colspan="3">GROUP TOTAL</td><td class="right">{group_total['pcba']:,}</td>
            <td class="right">{group_total['mat']:,}</td><td class="right">{group_total['fix']:,}</td>
            <td class="right">{group_total['sold']:,}</td><td class="right">{group_total['total']:,}</td></tr>
            </tbody></table></div>
            """
        html += f"""
        <div style="margin-top:20px;"><div class="grand-title">GRAND TOTAL</div>
        <table><tr><th>PCBA</th><th>Material</th><th>Fixing</th><th>Soldering</th><th>Total</th></tr>
        <tr><td class="right">{grand['pcba']:,}</td><td class="right">{grand['mat']:,}</td><td class="right">{grand['fix']:,}</td>
        <td class="right">{grand['sold']:,}</td><td class="right">{grand['total']:,}</td></tr></table></div>
        </body></html>
        """
        doc = QTextDocument()
        doc.setDefaultFont(QFont("Arial", 10))
        doc.setHtml(html)
        doc.setPageSize(QSizeF(printer.pageRect().size()))
        doc.setTextWidth(printer.pageRect().width())
        doc.print_(printer)

    def export_rework_report_csv(self):
        if self.report_layout.count() == 0:
            CustomMessageBox.show_warning(self, "Warning", "No data to export")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save CSV",
                                                   f"rework_aggregate_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                                   "CSV (*.csv)")
        if not filename:
            return
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["Line","Model","Fault Category","Sub Fault","PCBA","Material","Fixing","Soldering","Total"])
                for i in range(self.report_layout.count()):
                    widget = self.report_layout.itemAt(i).widget()
                    if isinstance(widget, QGroupBox) and "GRAND TOTAL" not in widget.title() and "PRODUCTION" not in widget.title():
                        title = widget.title()
                        line_match = re.search(r"LINE:\s*(\S+)", title, re.IGNORECASE)
                        model_match = re.search(r"MODEL:\s*(\S+)", title, re.IGNORECASE)
                        line = line_match.group(1) if line_match else ""
                        model = model_match.group(1) if model_match else ""
                        table = widget.findChild(QTableWidget)
                        if table:
                            for r in range(table.rowCount()):
                                if table.item(r,0) and table.item(r,0).text() == "TOTAL":
                                    continue
                                row_data = [line, model]
                                for c in range(table.columnCount()):
                                    item = table.item(r,c)
                                    row_data.append(item.text() if item else "")
                                writer.writerow(row_data)
            CustomMessageBox.show_success(self, "Success", f"Exported to {os.path.basename(filename)}")
        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Export failed: {str(e)}")

    def export_rework_report_excel(self):
        if not PANDAS_AVAILABLE:
            CustomMessageBox.show_warning(self, "Warning", "pandas not installed")
            return
        if self.report_layout.count() == 0:
            CustomMessageBox.show_warning(self, "Warning", "No data to export")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save Excel",
                                                   f"rework_aggregate_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                                   "Excel (*.xlsx)")
        if not filename:
            return
        try:
            data = []
            for i in range(self.report_layout.count()):
                widget = self.report_layout.itemAt(i).widget()
                if isinstance(widget, QGroupBox) and "GRAND TOTAL" not in widget.title() and "PRODUCTION" not in widget.title():
                    title = widget.title()
                    line_match = re.search(r"LINE:\s*(\S+)", title, re.IGNORECASE)
                    model_match = re.search(r"MODEL:\s*(\S+)", title, re.IGNORECASE)
                    line = line_match.group(1) if line_match else ""
                    model = model_match.group(1) if model_match else ""
                    table = widget.findChild(QTableWidget)
                    if table:
                        for r in range(table.rowCount()):
                            if table.item(r,0) and table.item(r,0).text() == "TOTAL":
                                continue
                            row_data = [line, model]
                            for c in range(table.columnCount()):
                                item = table.item(r,c)
                                row_data.append(item.text() if item else "")
                            data.append(row_data)
            columns = ["Line","Model","Fault Category","Sub Fault","PCBA","Material","Fixing","Soldering","Total"]
            df = pd.DataFrame(data, columns=columns)
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Rework Aggregate', index=False)
            CustomMessageBox.show_success(self, "Success", f"Exported to {os.path.basename(filename)}")
        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Export failed: {str(e)}")

    def export_csv(self):
        if self.report_table.rowCount() == 0:
            CustomMessageBox.show_warning(self, "Warning", "No data to export")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save CSV",
                                                   f"inspection_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                                   "CSV (*.csv)")
        if not filename:
            return
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["Date","Time","Station","Model","Employee Name","Employee ID","Line","Floor","Faults Count"])
                for row in range(self.report_table.rowCount()):
                    row_data = [self.report_table.item(row,col).text() for col in range(8)]
                    btn = self.report_table.cellWidget(row,8)
                    faults_count = re.findall(r'\d+', btn.text())[0] if btn else "0"
                    row_data.append(faults_count)
                    writer.writerow(row_data)
            CustomMessageBox.show_success(self, "Success", f"Exported to {os.path.basename(filename)}")
        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Export failed: {str(e)}")

    def export_excel(self):
        if not PANDAS_AVAILABLE:
            CustomMessageBox.show_warning(self, "Warning", "pandas not installed")
            return
        if self.report_table.rowCount() == 0:
            CustomMessageBox.show_warning(self, "Warning", "No data")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save Excel",
                                                   f"inspection_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                                   "Excel (*.xlsx)")
        if not filename:
            return
        try:
            data = []
            for row in range(self.report_table.rowCount()):
                row_data = [self.report_table.item(row,col).text() for col in range(8)]
                btn = self.report_table.cellWidget(row,8)
                faults_count = re.findall(r'\d+', btn.text())[0] if btn else "0"
                row_data.append(faults_count)
                data.append(row_data)
            df = pd.DataFrame(data, columns=["Date","Time","Station","Model","Employee Name","Employee ID","Line","Floor","Faults"])
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Inspections', index=False)
            CustomMessageBox.show_success(self, "Success", f"Exported to {os.path.basename(filename)}")
        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Export failed: {str(e)}")

    def export_rework_csv(self):
        if self.rework_table.rowCount() == 0 or (self.rework_table.rowCount() == 1 and "No rework root cause data" in self.rework_table.item(0,0).text()):
            CustomMessageBox.show_warning(self, "Warning", "No rework data to export")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save CSV",
                                                   f"rework_root_cause_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                                   "CSV (*.csv)")
        if not filename:
            return
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["Line","Model","Fault Category","Sub Fault","PCBA","Material","Fixing","Soldering","Total","Date"])
                for row in range(self.rework_table.rowCount()):
                    if self.rework_table.item(row,0) and "No rework root cause data" not in self.rework_table.item(row,0).text():
                        row_data = [self.rework_table.item(row,col).text() for col in range(10)]
                        writer.writerow(row_data)
            CustomMessageBox.show_success(self, "Success", f"Exported to {os.path.basename(filename)}")
        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Export failed: {str(e)}")

    def export_rework_excel(self):
        if not PANDAS_AVAILABLE:
            CustomMessageBox.show_warning(self, "Warning", "pandas not installed")
            return
        if self.rework_table.rowCount() == 0 or (self.rework_table.rowCount() == 1 and "No rework root cause data" in self.rework_table.item(0,0).text()):
            CustomMessageBox.show_warning(self, "Warning", "No rework data")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save Excel",
                                                   f"rework_root_cause_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                                   "Excel (*.xlsx)")
        if not filename:
            return
        try:
            data = []
            for row in range(self.rework_table.rowCount()):
                if self.rework_table.item(row,0) and "No rework root cause data" not in self.rework_table.item(row,0).text():
                    row_data = [self.rework_table.item(row,col).text() for col in range(10)]
                    data.append(row_data)
            df = pd.DataFrame(data, columns=["Line","Model","Fault Category","Sub Fault","PCBA","Material","Fixing","Soldering","Total","Date"])
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Rework Root Cause', index=False)
            CustomMessageBox.show_success(self, "Success", f"Exported to {os.path.basename(filename)}")
        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Export failed: {str(e)}")

    # ------------------------------------------------------------------
    # Helper methods for inspections
    # ------------------------------------------------------------------
    def parse_faults_from_defects(self, defects_text):
        faults = {}
        if not defects_text or defects_text == "No defects":
            return faults
        for line in defects_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^(.+?):\s*(\d+)\s*(?:pcs)?$', line, re.IGNORECASE)
            if m:
                faults[m.group(1).strip()] = int(m.group(2))
        return faults

    def extract_value(self, text, key):
        if not text:
            return None
        pat = rf'{key}\s*([^,\n]+)'
        m = re.search(pat, text)
        return m.group(1).strip() if m else None

    def generate_inspection_report(self):
        self.filtered_data = self.get_current_filtered_data()
        self.update_table(self.filtered_data)
        total_records = len(self.filtered_data)
        self.records_count.setText(f"📊 {total_records}")
        self.footer_label.setText(f"Showing {total_records} of {len(self.all_data)} records")
        if total_records > 0:
            total_faults = sum(r['defects_count'] for r in self.filtered_data)
            avg_faults = total_faults / total_records
            self.quick_stats.setText(f"⚡ Total Faults: {total_faults} | Avg: {avg_faults:.1f}")
        else:
            self.quick_stats.setText("")

    def get_current_filtered_data(self):
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        station = self.station_filter.currentText()
        search_text = self.search_input.text().lower()
        filtered = []
        for rec in self.all_data:
            if rec['date'] < date_from or rec['date'] > date_to:
                continue
            if station != "All" and rec['station'] != station:
                continue
            if search_text:
                found = any(search_text in rec.get(field, '').lower() for field in ['model','employee','employee_id','line','floor'])
                if not found:
                    for fault in rec['faults'].keys():
                        if search_text in fault.lower():
                            found = True
                            break
                    if not found:
                        continue
            filtered.append(rec)
        return filtered

    def update_table(self, data):
        self.report_table.setRowCount(len(data))
        for row, rec in enumerate(data):
            self.report_table.setItem(row, 0, QTableWidgetItem(rec['date']))
            self.report_table.setItem(row, 1, QTableWidgetItem(rec['time']))
            self.report_table.setItem(row, 2, QTableWidgetItem(rec['station']))
            self.report_table.setItem(row, 3, QTableWidgetItem(rec['model']))
            self.report_table.setItem(row, 4, QTableWidgetItem(rec['employee']))
            self.report_table.setItem(row, 5, QTableWidgetItem(rec['employee_id']))
            self.report_table.setItem(row, 6, QTableWidgetItem(rec['line']))
            self.report_table.setItem(row, 7, QTableWidgetItem(rec['floor']))

            faults_count = rec['defects_count']
            faults_data = rec['faults']
            btn = QPushButton(f"⚠ {faults_count}" if faults_count > 0 else "✓ 0")
            btn.setFixedSize(80, 28)
            if faults_count == 0:
                btn.setStyleSheet("background: #10B981; color: white; border-radius: 14px; font-weight: bold;")
            elif faults_count <= 5:
                btn.setStyleSheet("background: #F59E0B; color: white; border-radius: 14px; font-weight: bold;")
            else:
                btn.setStyleSheet("background: #EF4444; color: white; border-radius: 14px; font-weight: bold;")
            btn.clicked.connect(lambda _, f=faults_data: self.show_fault_details(f))
            self.report_table.setCellWidget(row, 8, btn)
        self.report_table.resizeRowsToContents()

    def show_fault_details(self, faults):
        if not faults:
            CustomMessageBox.show_info(self, "Info", "No fault details available")
            return
        dialog = FaultDetailsDialog(faults, self)
        dialog.exec_()

    def on_row_double_clicked(self, item):
        row = item.row()
        if row < len(self.filtered_data):
            self.open_edit_dialog(self.filtered_data[row])

    def open_edit_dialog(self, record):
        try:
            from widgets.new_entry_widget import NewEntryWidget
            edit_dialog = QDialog(self)
            edit_dialog.setWindowTitle("✏️ Edit Inspection Record")
            edit_dialog.setModal(True)
            edit_data = {
                'inspection_code': record.get('inspection_code', ''),
                'station': record.get('station', 'MMI Test'),
                'model': record.get('model', ''),
                'color': '',
                'shipment': '',
                'employee': record.get('employee', ''),
                'tester_id': record.get('employee_id', ''),
                'line': record.get('line', ''),
                'floor': record.get('floor', ''),
                'faults': record.get('faults', {}),
                'defects_count': record.get('defects_count', 0)
            }
            user_data = {'id': self.user_role, 'full_name': 'Admin', 'role': self.user_role}
            edit_widget = NewEntryWidget(self.db, user_data, edit_mode=True, edit_data=edit_data)
            layout = QVBoxLayout(edit_dialog)
            layout.addWidget(edit_widget)
            edit_widget.data_saved.connect(lambda: self.on_edit_saved(edit_dialog))
            edit_dialog.showMaximized()
            edit_dialog.exec_()
        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Failed to open edit: {str(e)}")

    def on_edit_saved(self, dialog):
        dialog.accept()
        self.load_inspections()
        CustomMessageBox.show_success(self, "Success", "Record updated!")

    def refresh(self):
        self.load_inspections()
        self.load_completed_rework()
        self.load_rework_report()

    # ------------------------------------------------------------------
    # Methods for existing tabs (line/model/fault categories)
    # ------------------------------------------------------------------
    def load_line_model_options(self):
        self.line_model_map = {}
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT line, model 
                    FROM rework_root_cause 
                    WHERE line IS NOT NULL AND line != '' 
                    AND model IS NOT NULL AND model != ''
                    ORDER BY line, model
                """)
                rows = cursor.fetchall()
                all_lines = set()
                all_models = set()
                for line, model in rows:
                    all_lines.add(line)
                    all_models.add(model)
                    self.line_model_map.setdefault(line, []).append(model)

                self.report_line_filter.blockSignals(True)
                self.report_line_filter.clear()
                self.report_line_filter.addItem("All")
                for line in sorted(all_lines):
                    self.report_line_filter.addItem(line)
                self.report_line_filter.blockSignals(False)

                self.all_models = sorted(all_models)
                self.report_model_filter.blockSignals(True)
                self.report_model_filter.clear()
                self.report_model_filter.addItem("All")
                for model in self.all_models:
                    self.report_model_filter.addItem(model)
                self.report_model_filter.blockSignals(False)

                self.report_line_filter.currentTextChanged.disconnect()
                self.report_line_filter.currentTextChanged.connect(self.on_line_changed)
        except Exception as e:
            print(f"Error loading line/model options: {e}")

    def on_line_changed(self, line):
        if not hasattr(self, 'all_models') or self.all_models is None:
            return
        current_model = self.report_model_filter.currentText()
        self.report_model_filter.blockSignals(True)
        self.report_model_filter.clear()
        self.report_model_filter.addItem("All")
        models = self.all_models if line == "All" else self.line_model_map.get(line, [])
        for model in sorted(models):
            self.report_model_filter.addItem(model)
        index = self.report_model_filter.findText(current_model)
        self.report_model_filter.setCurrentIndex(index if index >= 0 else 0)
        self.report_model_filter.blockSignals(False)

    def load_fault_categories(self):
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT fault_category FROM rework_root_cause WHERE fault_category IS NOT NULL AND fault_category != '' ORDER BY fault_category")
                rows = cursor.fetchall()
                self.report_fault_filter.clear()
                self.report_fault_filter.addItem("All")
                for row in rows:
                    self.report_fault_filter.addItem(row[0])
        except Exception as e:
            print(f"Error loading fault categories: {e}")