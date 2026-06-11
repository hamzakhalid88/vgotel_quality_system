import csv, re, os, datetime, html as html_escape
from typing import Dict, List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate, QTimer, QSizeF, QMarginsF
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5.QtGui import QPageLayout, QPageSize, QColor, QFont, QTextDocument
from database import Database
import datetime
 
from custom_dialogs import CustomMessageBox
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Inline RootCauseDialog - no external dependency needed
# ----------------------------------------------------------------------
class RootCauseDialog(QDialog):
    """Dialog to edit root cause mapping for a specific fault category/subcategory."""

    def __init__(self, db, fault_category, fault_subcategory, existing_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.fault_category = fault_category
        self.fault_subcategory = fault_subcategory
        self.existing_data = existing_data or {}
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(f"Edit Root Cause - {self.fault_category}")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        self.setStyleSheet("background-color: #f8fafc;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel(f"🔧 Root Cause Mapping")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        layout.addWidget(header)

        # Info section
        info_frame = QFrame()
        info_frame.setStyleSheet("background: #e0f2fe; border-radius: 8px; padding: 10px;")
        info_layout = QVBoxLayout(info_frame)

        cat_label = QLabel(f"<b>Fault Category:</b> {self.fault_category}")
        cat_label.setStyleSheet("font-size: 13px; color: #0369a1;")
        info_layout.addWidget(cat_label)

        sub_label = QLabel(f"<b>Sub Category:</b> {self.fault_subcategory or 'N/A'}")
        sub_label.setStyleSheet("font-size: 13px; color: #0369a1;")
        info_layout.addWidget(sub_label)

        layout.addWidget(info_frame)

        # Form fields
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # Root Cause
        self.root_cause_input = QTextEdit()
        self.root_cause_input.setPlaceholderText("Enter root cause analysis...")
        self.root_cause_input.setText(self.existing_data.get('root_cause', ''))
        self.root_cause_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                background: white;
            }
        """)
        self.root_cause_input.setMaximumHeight(80)
        form_layout.addRow("Root Cause:", self.root_cause_input)

        # Responsible Department
        self.responsible_input = QLineEdit()
        self.responsible_input.setPlaceholderText("e.g., SMT, Assembly, Quality...")
        self.responsible_input.setText(self.existing_data.get('responsible', ''))
        self.responsible_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                background: white;
            }
        """)
        form_layout.addRow("Responsible Dept:", self.responsible_input)

        # Solution Plan
        self.solution_input = QTextEdit()
        self.solution_input.setPlaceholderText("Enter solution/action plan...")
        self.solution_input.setText(self.existing_data.get('solution', ''))
        self.solution_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                background: white;
            }
        """)
        self.solution_input.setMaximumHeight(80)
        form_layout.addRow("Solution Plan:", self.solution_input)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("💾 Save")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedSize(100, 35)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #2563eb;
            }
        """)
        save_btn.clicked.connect(self.save_mapping)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedSize(100, 35)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #475569;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #e2e8f0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def save_mapping(self):
        """Save or update the root cause mapping in the database."""
        root_cause = self.root_cause_input.toPlainText().strip()
        responsible = self.responsible_input.text().strip()
        solution = self.solution_input.toPlainText().strip()

        try:
            with self.db.get_connection() as conn:
                c = conn.cursor()

                # Check if record exists (case-insensitive match)
                c.execute("""
                    SELECT id FROM rework_resolution_mapping 
                    WHERE LOWER(LTRIM(RTRIM(fault_category))) = LOWER(LTRIM(RTRIM(?))) 
                    AND LOWER(LTRIM(RTRIM(COALESCE(fault_subcategory, '')))) = LOWER(LTRIM(RTRIM(COALESCE(?, ''))))
                """, (self.fault_category, self.fault_subcategory or ''))

                existing = c.fetchone()

                if existing:
                    # UPDATE existing record
                    c.execute("""
                        UPDATE rework_resolution_mapping 
                        SET root_cause = ?, 
                            responsible_dept = ?, 
                            solution_plan = ?,
                            updated_at = GETDATE()
                        WHERE id = ?
                    """, (root_cause, responsible, solution, existing[0]))
                else:
                    # INSERT new record
                    c.execute("""
                        INSERT INTO rework_resolution_mapping 
                        (fault_category, fault_subcategory, root_cause, responsible_dept, solution_plan)
                        VALUES (?, ?, ?, ?, ?)
                    """, (self.fault_category, self.fault_subcategory or '', root_cause, responsible, solution))

                conn.commit()

            CustomMessageBox.show_success(self, "Success", "✅ Root cause mapping saved successfully!")
            self.accept()

        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Failed to save: {str(e)}")

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
        self.setStyleSheet("background-color: #f8fafc;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20,20,20,20)
        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("🔍"))
        title = QLabel("Fault Breakdown")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        header.addWidget(title)
        header.addStretch()
        total = sum(self.faults_data.values()) if self.faults_data else 0
        badge = QLabel(f"Total: {total}")
        badge.setStyleSheet("background: #e2e8f0; color: #475569; padding: 5px 12px; border-radius: 20px; font-weight: bold;")
        header.addWidget(badge)
        layout.addLayout(header)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #e2e8f0; margin: 5px 0;")
        layout.addWidget(sep)
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
                background: #1e293b;
                color: white;
                padding: 12px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-bottom: 2px solid #334155;
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
        if self.faults_data:
            sorted_faults = sorted(self.faults_data.items(), key=lambda x: x[1], reverse=True)
            self.fault_table.setRowCount(len(sorted_faults))
            for row, (fault, qty) in enumerate(sorted_faults):
                self.fault_table.setItem(row,0, QTableWidgetItem(fault))
                qty_item = QTableWidgetItem(str(qty))
                qty_item.setTextAlignment(Qt.AlignCenter)
                if qty >= 30: qty_item.setForeground(QColor("#991b1b")); qty_item.setBackground(QColor("#fee2e2"))
                elif qty >= 20: qty_item.setForeground(QColor("#9a3412")); qty_item.setBackground(QColor("#ffedd5"))
                elif qty >= 10: qty_item.setForeground(QColor("#b45309")); qty_item.setBackground(QColor("#fef3c7"))
                elif qty >= 5: qty_item.setForeground(QColor("#d97706")); qty_item.setBackground(QColor("#fffbeb"))
                elif qty > 0: qty_item.setForeground(QColor("#15803d")); qty_item.setBackground(QColor("#dcfce7"))
                else: qty_item.setForeground(QColor("#64748b"))
                self.fault_table.setItem(row,1, qty_item)
        else:
            self.fault_table.setRowCount(1)
            no = QTableWidgetItem("✨ No faults recorded for this inspection")
            no.setTextAlignment(Qt.AlignCenter)
            no.setForeground(QColor("#64748b"))
            self.fault_table.setSpan(0,0,1,2)
            self.fault_table.setItem(0,0, no)
        layout.addWidget(self.fault_table)
        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setFixedSize(90,35)
        copy_btn.setStyleSheet("background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 8px; font-weight: bold;")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(copy_btn)
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(100,35)
        close_btn.setStyleSheet("background: #3b82f6; color: white; border: none; border-radius: 8px; font-weight: bold;")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    def copy_to_clipboard(self):
        if not self.faults_data:
            QApplication.clipboard().setText("No faults recorded")
            CustomMessageBox.show_info(self, "Info", "✅ Copied to clipboard!")
            return
        lines = ["FAULT BREAKDOWN", "="*50, f"Total Faults: {sum(self.faults_data.values())}", f"Fault Types: {len(self.faults_data)}", "="*50, ""]
        for f,q in sorted(self.faults_data.items(), key=lambda x:x[1], reverse=True):
            lines.append(f"{f}: {q} pcs")
        QApplication.clipboard().setText("\n".join(lines))
        CustomMessageBox.show_info(self, "Success", "✅ Fault data copied!")

# ----------------------------------------------------------------------
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
            # Ensure rework_resolution_mapping exists
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
            # Also ensure columns exist if table was created by older version
            try:
                c.execute("ALTER TABLE rework_resolution_mapping ADD model NVARCHAR(100)")
            except:
                pass
            try:
                c.execute("ALTER TABLE rework_resolution_mapping ADD ship_no NVARCHAR(50)")
            except:
                pass
            try:
                c.execute("ALTER TABLE rework_resolution_mapping ADD record_date DATE")
            except:
                pass
            try:
                c.execute("ALTER TABLE rework_resolution_mapping ADD is_weak_point BIT DEFAULT 0")
            except:
                pass
            conn.commit()

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
        self.tab_widget.addTab(self.inspections_tab, "📋 Inspections")
        self.tab_widget.addTab(self.rework_tab, "✅ Rework Complete")
        self.tab_widget.addTab(self.rework_report_tab, "📊 Rework Report")
        self.tab_widget.addTab(self.line_summary_tab, "🔧 Rework Summary")
        main.addWidget(self.tab_widget)

    # --------------------------- helpers for UI creation ---------------------------
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
        if color == "#00b4d8": return "#0096c7"
        if color == "#28a745": return "#218838"
        if color == "#ffc107": return "#e0a800"
        if color == "#0f2027": return "#1a2a3a"
        if color == "#475569": return "#334155"
        if color == "#1E3A5F": return "#152b44"
        if color == "#6B7280": return "#4b5563"
        return color

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
        # filters
        self.date_from = QDateEdit(QDate(2000,1,1)); self.date_from.setCalendarPopup(True)
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        self.station_filter = QComboBox()
        self.station_filter.addItems(["All","Semi Test","MMI Test","Appearance Test","Final Test"])
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Model, Employee, ID, Fault, Line, Floor...")
        gen_btn = self._btn("🔄 Refresh", "#00b4d8", self.generate_inspection_report)
        export_btn = self._btn("📥 CSV", "#28a745", self.export_csv)
        widgets = [
            QLabel("📅 From:"), self.date_from,
            QLabel("To:"), self.date_to,
            QFrame(styleSheet="background: #ddd; max-width: 1px;"),
            QLabel("🏭 Station:"), self.station_filter,
            QFrame(styleSheet="background: #ddd; max-width: 1px;"),
            QLabel("🔎 Search:"), self.search_input, gen_btn, export_btn
        ]
        if PANDAS_AVAILABLE:
            excel_btn = self._btn("📊 Excel", "#ffc107", self.export_excel)
            widgets.append(excel_btn)
        layout.addWidget(self._simple_filter_frame(widgets))
        # table
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
        # footer
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
        # connect signals
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
        for w in [QLabel("Line:"), self.rework_line_filter, QLabel("Model:"), self.rework_model_filter]:
            w.setStyleSheet("font-size: 11px;")
        filter_layout.addWidget(QLabel("Line:")); filter_layout.addWidget(self.rework_line_filter)
        filter_layout.addWidget(QLabel("Model:")); filter_layout.addWidget(self.rework_model_filter)
        filter_layout.addStretch(); filter_layout.addWidget(refresh)
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
    def setup_rework_report_tab(self):
        layout = QVBoxLayout(self.rework_report_tab)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(10)
        self.report_total_label = QLabel("")
        self.report_total_label.setStyleSheet("color: #00e5ff; font-weight: bold; background: rgba(0,0,0,0.3); padding: 5px 12px; border-radius: 20px;")
        layout.addWidget(self._header_frame("📊 REWORK AGGREGATE REPORT", self.report_total_label))
        # filter panel
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
    def setup_line_rework_summary_tab(self):
        layout = QVBoxLayout(self.line_summary_tab)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(10)
        layout.addWidget(self._header_frame("🔧 LINE REWORK SUMMARY (Full Breakdown)", None))

        # filters panel
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
        edit_rc_btn = self._btn("✏️ Edit Root Cause", "#1E3A5F", self.open_root_cause_dialog)   # <--- NEW BUTTON

        grid.addWidget(QLabel("Line:"),0,0); grid.addWidget(self.summary_line_combo,0,1)
        grid.addWidget(QLabel("Model:"),0,2); grid.addWidget(self.summary_model_combo,0,3)
        grid.addWidget(QLabel("From:"),0,4); grid.addWidget(self.summary_date_from,0,5)
        grid.addWidget(QLabel("To:"),0,6); grid.addWidget(self.summary_date_to,0,7)
        grid.addWidget(QLabel("Fault Category:"),1,0); grid.addWidget(self.summary_cat_combo,1,1)
        grid.addWidget(QLabel("Sub-Fault:"),1,2); grid.addWidget(self.summary_sub_combo,1,3)
        grid.addWidget(gen_btn,2,0,1,2)
        grid.addWidget(html_btn,2,2,1,2)
        grid.addWidget(print_btn,2,4,1,2)
        grid.addWidget(edit_rc_btn,2,6,1,2)   # <--- NEW BUTTON PLACEMENT
        grid.setColumnStretch(7,1)
        layout.addWidget(panel)

        # QTextEdit with full stretch
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

    # ------------------------- Line Summary helpers -------------------------
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

    # ------------------------- open root cause dialog (NEW) -------------------------
    def open_root_cause_dialog(self):
        """Open RootCauseDialog to edit root cause mapping."""
        cat = self.summary_cat_combo.currentText()
        sub = self.summary_sub_combo.currentText()
        
        if cat == "All Categories" or not cat:
            CustomMessageBox.show_warning(self, "Warning", 
                "Please select a specific Fault Category first!")
            return
        
        # Load existing data
        existing_data = {}
        rows = self.db.execute_query("""
            SELECT root_cause, responsible_dept, solution_plan 
            FROM rework_resolution_mapping 
            WHERE LOWER(LTRIM(RTRIM(fault_category))) = LOWER(LTRIM(RTRIM(?)))
            AND LOWER(LTRIM(RTRIM(fault_subcategory))) = LOWER(LTRIM(RTRIM(?)))
        """, (cat, sub or ''), fetch_all=True)
        
        if rows:
            existing_data = {
                'root_cause': rows[0]['root_cause'] or '',
                'responsible': rows[0]['responsible_dept'] or '',
                'solution': rows[0]['solution_plan'] or ''
            }
        
        # Open new dialog
        dlg = RootCauseDialog(self.db, cat, sub if sub != "All Sub-Faults" else '', 
                            existing_data, self)
        
        if dlg.exec_() == QDialog.Accepted:
            self.generate_line_rework_summary()  # Auto refresh
            
    # ------------------------- generate line rework summary -------------------------
    def load_resolution_mapping(self):
        rows = self.db.execute_query("""
            SELECT fault_category, fault_subcategory, root_cause, 
                responsible_dept, solution_plan 
            FROM rework_resolution_mapping
        """, fetch_all=True)
        mapping = {}
        for r in rows:
            cat = (r['fault_category'] or '').strip().lower()
            sub = (r['fault_subcategory'] or '').strip().lower()  # <-- FIX: lowercase
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
                model,
                fault_category,
                fault_subcategory,
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
            query += " AND line=?"
            params.append(line)

        if model and model != "All Models":
            query += " AND model=?"
            params.append(model)

        if cat and cat != "All Categories":
            query += " AND fault_category=?"
            params.append(cat)

        if sub and sub != "All Sub-Faults":
            query += " AND fault_subcategory=?"
            params.append(sub)

        query += """
            GROUP BY
                line,
                model,
                fault_category,
                fault_subcategory
            ORDER BY
                line,
                model,
                total_rework DESC
        """

        rows = self.db.execute_query(
            query,
            tuple(params),
            fetch_all=True
        )

        if not rows:
            self.summary_output.setHtml(f"""
            <html>
            <body style="font-family:Arial;padding:20px;">
                <div style="
                    background:#fee2e2;
                    color:#b91c1c;
                    padding:15px;
                    border-radius:8px;">
                    <b>No Data Found</b>
                </div>
            </body>
            </html>
            """)
            return

        mapping = self.load_resolution_mapping()

        lines_data = {}
        for r in rows:
            lines_data.setdefault(
                r["line"], {}
            ).setdefault(
                r["model"], []
            ).append(r)

        totals = {
            "pcba": 0,
            "material": 0,
            "fixing": 0,
            "soldering": 0,
            "total": 0
        }

        for r in rows:
            totals["pcba"] += r["total_pcba"]
            totals["material"] += r["total_material"]
            totals["fixing"] += r["total_fixing"]
            totals["soldering"] += r["total_soldering"]
            totals["total"] += r["total_rework"]

        cat_totals = {}
        for r in rows:
            fc = r["fault_category"]
            cat_totals[fc] = (
                cat_totals.get(fc, 0)
                + r["total_rework"]
            )

        top_cats = sorted(
            cat_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        html = self._render_summary_html(
            lines_data,
            totals,
            top_cats,
            mapping,
            line,
            model,
            cat,
            sub,
            ignore_date,
            date_from,
            date_to
        )

        self.summary_output.clear()
        self.summary_output.setHtml(html)
        self.summary_output.repaint()

    def _render_summary_html(self, lines_data, totals, top_cats, mapping,
                            line, model, cat, sub, ignore_date, date_from, date_to):
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
        .sub {
            margin-top: 10px;
            margin-bottom: 6px;
            font-weight: bold;
            font-size: 14px;
            color: #1f2937;
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
        ul {
            padding-left: 20px;
        }
        li {
            margin-bottom: 10px;
        }
        /* Screen-only styles - print handled by print_line_summary */
        @media screen {
            body {
                font-size: 14px;
                padding: 10px;
            }
        }
        </style></head><body>"""

        # Title & filters
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

        # Total Rework Volume table
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

        # Detailed Breakdown – each line in a separate div with class "line-group"
        html += "<div class='section'>Detailed Breakdown</div>"
        first_line = True
        for line_name, models in lines_data.items():
            if not first_line:
                html += '<div class="line-group">'
            else:
                html += '<div>'
                first_line = False
            html += f"<div class='sub'>Line: {line_name}</div>"

            for model_name, faults in models.items():
                html += f"<div class='sub'>Model: {model_name}</div>"
                html += '<table width="100%" cellspacing="0" cellpadding="0" style="table-layout:fixed;">'
                html += """
                <tr>
                    <th style="width:18%; text-align:left;">Fault</th>
                    <th style="width:12%; text-align:left;">Sub</th>
                    <th style="width:6%; text-align:center;">PCBA</th>
                    <th style="width:6%; text-align:center;">Mat</th>
                    <th style="width:6%; text-align:center;">Fix</th>
                    <th style="width:6%; text-align:center;">Sold</th>
                    <th style="width:6%; text-align:center;">Total</th>
                    <th style="width:22%; text-align:left;">Root Cause</th>
                    <th style="width:12%; text-align:left;">Resp.</th>
                    <th style="width:12%; text-align:left;">Solution</th>
                </tr>
                """
                for f in faults:
                    key = (f['fault_category'].strip().lower(), 
                        (f['fault_subcategory'] or '').strip().lower())
                    m = mapping.get(key, {})
                    html += f"""
                    <tr>
                        <td style="width:18%; text-align:left; word-wrap:break-word;">{f['fault_category']}</td>
                        <td style="width:12%; text-align:left; word-wrap:break-word;">{f['fault_subcategory'] or '-'}</td>
                        <td style="width:6%; text-align:center;">{f['total_pcba']:,}</td>
                        <td style="width:6%; text-align:center;">{f['total_material']:,}</td>
                        <td style="width:6%; text-align:center;">{f['total_fixing']:,}</td>
                        <td style="width:6%; text-align:center;">{f['total_soldering']:,}</td>
                        <td style="width:6%; text-align:center; font-weight:bold;">{f['total_rework']:,}</td>
                        <td style="width:22%; text-align:left; word-wrap:break-word;">{m.get('root_cause','-')}</td>
                        <td style="width:12%; text-align:left; word-wrap:break-word;">{m.get('responsible','-')}</td>
                        <td style="width:12%; text-align:left; word-wrap:break-word;">{m.get('solution','-')}</td>
                    </tr>
                    """
                html += "</table>"
            html += "</div>"  # close line-group div

        # Top Issues
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

        # Strip existing @media print styles from the HTML to prevent conflicts
        import re
        # Remove any existing @media print blocks
        html = re.sub(r'@media\s+print\s*\{[^}]*\}', '', html, flags=re.DOTALL)
        # Remove any existing @page rules
        html = re.sub(r'@page\s*\{[^}]*\}', '', html, flags=re.DOTALL)

        print_css = """
        <style>
            /* === PROFESSIONAL PRINT STYLES === */
            @page {
                size: A4 landscape;
                margin: 8mm 6mm;
            }

            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }

            body {
                font-family: 'Segoe UI', 'Arial', sans-serif !important;
                font-size: 9pt !important;
                line-height: 1.25 !important;
                color: #1f2937 !important;
                background: white !important;
                margin: 0 !important;
                padding: 0 !important;
            }

            /* Title */
            .title {
                font-size: 13pt !important;
                font-weight: 700 !important;
                text-align: center !important;
                padding: 6px 10px !important;
                margin-bottom: 6px !important;
                background: #0f172a !important;
                color: white !important;
                border-radius: 3px !important;
                page-break-after: avoid !important;
            }

            /* Filter info bar */
            .filters {
                font-size: 7.5pt !important;
                padding: 4px 8px !important;
                margin-bottom: 6px !important;
                background: #f8fafc !important;
                border: 1px solid #cbd5e1 !important;
                border-radius: 3px !important;
                color: #475569 !important;
                page-break-after: avoid !important;
            }

            /* Section headers */
            .section {
                font-size: 10pt !important;
                font-weight: 700 !important;
                padding: 5px 8px !important;
                margin-top: 8px !important;
                margin-bottom: 4px !important;
                background: #e2e8f0 !important;
                border-left: 3px solid #0f172a !important;
                border-radius: 2px !important;
                color: #0f172a !important;
                page-break-after: avoid !important;
            }

            /* Sub headers (Line/Model) */
            .sub {
                font-size: 9pt !important;
                font-weight: 700 !important;
                margin-top: 6px !important;
                margin-bottom: 3px !important;
                color: #334155 !important;
                page-break-after: avoid !important;
            }

            /* Tables - CRITICAL for alignment */
            table {
                width: 100% !important;
                border-collapse: collapse !important;
                font-size: 7pt !important;
                margin-bottom: 4px !important;
                table-layout: fixed !important;
                page-break-inside: auto !important;
            }

            thead {
                display: table-header-group !important;
            }

            tr {
                page-break-inside: avoid !important;
                page-break-after: auto !important;
            }

            th {
                background: #1e293b !important;
                color: white !important;
                padding: 3px 4px !important;
                font-size: 7pt !important;
                font-weight: 600 !important;
                text-align: center !important;
                border: 1px solid #334155 !important;
                white-space: normal !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                line-height: 1.2 !important;
            }

            td {
                padding: 2px 4px !important;
                font-size: 7pt !important;
                border: 1px solid #e2e8f0 !important;
                vertical-align: top !important;
                word-wrap: break-word !important;
                overflow-wrap: break-word !important;
                line-height: 1.2 !important;
            }

            /* Column alignment fixes */
            td[align="right"] {
                text-align: right !important;
                font-family: 'Consolas', 'Courier New', monospace !important;
            }

            td[align="center"] {
                text-align: center !important;
            }

            td[style*="width:18%"] {
                width: 18% !important;
            }
            td[style*="width:12%"] {
                width: 12% !important;
            }
            td[style*="width:6%"] {
                width: 6% !important;
                text-align: center !important;
            }
            td[style*="width:22%"] {
                width: 22% !important;
            }

            /* Alternating rows */
            tr:nth-child(even) {
                background: #f8fafc !important;
            }

            tr:nth-child(odd) {
                background: white !important;
            }

            /* Grand total row */
            .grand-row td {
                background: #e2e8f0 !important;
                font-weight: 700 !important;
                border-top: 2px solid #94a3b8 !important;
            }

            /* Top Issues list */
            ul {
                padding-left: 14px !important;
                margin: 4px 0 !important;
            }

            li {
                margin-bottom: 3px !important;
                font-size: 7.5pt !important;
                line-height: 1.3 !important;
            }

            /* Page break control */
            .line-group {
                page-break-before: auto !important;
            }

            .line-group:first-of-type {
                page-break-before: avoid !important;
            }

            /* Footer timestamp */
            .filters:last-child {
                font-size: 6.5pt !important;
                color: #64748b !important;
                margin-top: 8px !important;
                border: none !important;
                background: transparent !important;
            }

            /* Bold numbers in total column */
            td b {
                font-weight: 700 !important;
                color: #0f172a !important;
            }

            /* Ensure text doesn't overflow */
            td, th {
                max-width: 200px !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }
        </style>
        """

        # Rebuild the HTML with clean structure
        # Extract body content
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
        if body_match:
            body_content = body_match.group(1)
        else:
            body_content = html

        # Build clean HTML with professional print CSS
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

    # ------------------------- data loading methods -------------------------
    def load_inspections(self):
        self.all_data = []
        rows = self.db.execute_query("""
            SELECT inspection_code, inspection_date, inspection_type, defects, remarks, rejected_quantity, line, floor
            FROM inspections WHERE product_id IS NULL OR inspection_type IN ('MMI Test','Semi Test','Appearance Test','Final Test')
            ORDER BY inspection_date DESC
        """, fetch_all=True)
        for row in rows:
            defects_text = row['defects'] or ""
            faults = self._parse_faults(defects_text)
            recalc = sum(faults.values())
            rej = row['rejected_quantity'] or 0
            defects_count = recalc if recalc>0 else rej
            if rej>0 and not faults: faults["Total Faults"] = rej
            remarks = row['remarks'] or ""
            insp_date = row['inspection_date'] or datetime.datetime.now()
            self.all_data.append({
                'date': insp_date.strftime('%Y-%m-%d'), 'time': insp_date.strftime('%H:%M:%S'),
                'station': row['inspection_type'] or 'MMI Test',
                'model': self._extract(remarks,"Model:") or "N/A",
                'employee': self._extract(remarks,"Employee:") or "N/A",
                'employee_id': self._extract(remarks,"Employee ID:") or self._extract(remarks,"Tester ID:") or "N/A",
                'line': row['line'] or "N/A", 'floor': row['floor'] or "N/A",
                'defects_count': defects_count, 'faults': faults, 'inspection_code': row['inspection_code'] or ''
            })
        self.generate_inspection_report()

    def _parse_faults(self, txt):
        faults = {}
        if not txt or txt=="No defects": return faults
        for line in txt.split('\n'):
            m = re.match(r'^(.+?):\s*(\d+)\s*(?:pcs)?$', line.strip(), re.I)
            if m: faults[m.group(1).strip()] = int(m.group(2))
        return faults

    def _extract(self, text, key):
        if not text: return None
        m = re.search(rf'{key}\s*([^,\n]+)', text)
        return m.group(1).strip() if m else None

    def generate_inspection_report(self):
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        station = self.station_filter.currentText()
        search_text = self.search_input.text().lower()
        self.filtered_data = []
        for r in self.all_data:
            if r['date'] < date_from or r['date'] > date_to: continue
            if station != "All" and r['station'] != station: continue
            if search_text:
                found = any(search_text in str(r.get(f,'')).lower() for f in ['model','employee','employee_id','line','floor'])
                if not found:
                    found = any(search_text in f.lower() for f in r['faults'].keys())
                if not found: continue
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
        dlg = QDialog(self)
        dlg.setWindowTitle("✏️ Edit Inspection Record")
        dlg.setModal(True)
        edit_data = {
            'inspection_code': rec.get('inspection_code',''), 'station': rec.get('station','MMI Test'),
            'model': rec.get('model',''), 'employee': rec.get('employee',''), 'tester_id': rec.get('employee_id',''),
            'line': rec.get('line',''), 'floor': rec.get('floor',''), 'faults': rec.get('faults',{}),
            'defects_count': rec.get('defects_count',0)
        }
        widget = NewEntryWidget(self.db, {'id':self.user_role,'full_name':'Admin','role':self.user_role}, edit_mode=True, edit_data=edit_data)
        layout = QVBoxLayout(dlg); layout.addWidget(widget)
        widget.data_saved.connect(lambda: (dlg.accept(), self.load_inspections(), CustomMessageBox.show_success(self,"Success","Record updated!")))
        dlg.showMaximized(); dlg.exec_()

    # ------------------------- Rework Root Cause (Tab2) -------------------------
    def load_completed_rework(self):
        line = self.rework_line_filter.text().strip()
        model = self.rework_model_filter.text().strip()
        query = "SELECT record_date, line, model, fault_category, fault_subcategory, pcba_qty, material_qty, fixing_qty, soldering_qty, total_qty FROM rework_root_cause WHERE 1=1"
        params = []
        if line: query += " AND line LIKE ?"; params.append(f"%{line}%")
        if model: query += " AND model LIKE ?"; params.append(f"%{model}%")
        rows = self.db.execute_query(query, tuple(params), fetch_all=True)
        headers = ["Date","Line","Model","Fault Category","Sub Fault","PCBA","Material","Fixing","Soldering","Total"]
        self.rework_table.setColumnCount(len(headers))
        self.rework_table.setHorizontalHeaderLabels(headers)
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
            date_str = r['record_date'].strftime('%Y-%m-%d') if r['record_date'] else ''
            self.rework_table.setItem(i,0, QTableWidgetItem(date_str))
            self.rework_table.setItem(i,1, QTableWidgetItem(str(r['line'])))
            self.rework_table.setItem(i,2, QTableWidgetItem(str(r['model'])))
            self.rework_table.setItem(i,3, QTableWidgetItem(str(r['fault_category'])))
            self.rework_table.setItem(i,4, QTableWidgetItem(str(r['fault_subcategory'])))
            for col,key in enumerate(['pcba_qty','material_qty','fixing_qty','soldering_qty','total_qty'],5):
                val = r[key] or 0
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.rework_table.setItem(i,col, item)
                if key=='total_qty': total += val
        self.rework_total_label.setText(f"Total Units: {total}")
        widths = [90,80,100,150,150,60,60,60,60,70]
        for i,w in enumerate(widths): self.rework_table.setColumnWidth(i,w)

    # ------------------------- Rework Report (Tab3) -------------------------
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

    # ------------------------- Print & Export for Rework Report -------------------------
    def print_rework_report(self):
        html = self._build_report_html()
        if html: self._print_html(html)

    def _build_report_html(self):
        date_from = self.report_date_from.date().toString("yyyy-MM-dd")
        date_to = self.report_date_to.date().toString("yyyy-MM-dd")
        line = self.report_line_filter.currentText()
        model = self.report_model_filter.currentText()
        fault = self.report_fault_filter.currentText()
        rows = self.db.execute_query("""
            SELECT record_date, line, model, fault_category, fault_subcategory,
                pcba_qty, material_qty, fixing_qty, soldering_qty, total_qty
            FROM rework_root_cause WHERE record_date BETWEEN ? AND ?
        """ + (f" AND line='{line}'" if line != "All" else "") + (f" AND model='{model}'" if model != "All" else "") + (f" AND fault_category='{fault}'" if fault != "All" else ""),
            (date_from, date_to), fetch_all=True)
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
            h2 {
                text-align: center;
                margin-bottom: 10px;
                color: #0f2027;
            }
            h3 {
                background: #e2e8f0;
                padding: 5px 10px;
                margin: 15px 0 10px 0;
                font-size: 12pt;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 15px;
                font-size: 9pt;
                table-layout: fixed;
            }
            th, td {
                border: 1px solid #999;
                padding: 4px 6px;
                text-align: left;
                vertical-align: top;
                word-wrap: break-word;
            }
            th {
                background: #d9e2f3;
                font-weight: bold;
            }
            .right {
                text-align: right;
            }
            .group-total {
                background: #fff2cc;
                font-weight: bold;
            }
            @media print {
                @page {
                    margin: 5mm;
                    size: A4 landscape;
                }
                html, body {
                    width: 100%;
                    margin: 0 !important;
                    padding: 0 !important;
                    background: white;
                }
                body {
                    font-size: 12pt;
                    padding: 0;
                }
                h2 {
                    font-size: 18pt;
                    page-break-after: avoid;
                }
                h3 {
                    font-size: 14pt;
                    background: #eee;
                    page-break-after: avoid;
                }
                table {
                    font-size: 11pt;
                    width: 100%;
                    table-layout: auto;
                    page-break-inside: auto;
                }
                tr {
                    page-break-inside: avoid;
                    page-break-after: auto;
                }
                th, td {
                    padding: 5px 8px;
                }
                th {
                    background: #ccc !important;
                    color: black !important;
                }
                .right {
                    text-align: right;
                }
                .group-total {
                    background: #ffffcc !important;
                }
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
            from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
            from PyQt5.QtGui import QTextDocument, QFont
            from PyQt5.QtCore import Qt, QSizeF

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

    # ------------------------- remaining exports for inspections -------------------------
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

    # ------------------------- line/model/fault options -------------------------
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

    def refresh(self):
        self.load_inspections()
        self.load_completed_rework()
        self.load_rework_report()