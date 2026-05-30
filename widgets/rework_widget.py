import sys
import os
import uuid
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QHeaderView, QSpinBox, QGroupBox,
    QFileDialog, QFrame, QSizePolicy, QApplication, QScrollArea,
    QMessageBox, QDateEdit, QProgressDialog,QProgressBar,QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate, QThread, QObject
from PyQt5.QtGui import QFont
from database import Database
from custom_dialogs import CustomMessageBox
import pandas as pd

PANDAS_AVAILABLE = True

# ----------------------------------------------------------------------
# Background Thread for Processing
# ----------------------------------------------------------------------
class ProcessWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str, object)
    error = pyqtSignal(str)

    def __init__(self, sheet_type, df, user, inspection_date=None):
        super().__init__()
        self.sheet_type = sheet_type
        self.df = df
        self.user = user
        self.inspection_date = inspection_date

    def _clean_str(self, val):
        if pd.isna(val):
            return ""
        return str(val).strip()

    def _clean_int(self, val):
        if pd.isna(val):
            return 0
        if isinstance(val, str):
            val = val.strip()
            if val == '' or val == '-' or val.upper() == 'N/A':
                return 0
        try:
            return int(float(val))
        except:
            return 0

    def _parse_date(self, val):
        if val is None:
            return None
        if hasattr(val, 'date'):
            return val.date()
        date_str = str(val).strip()
        if not date_str:
            return None
        if ' ' in date_str:
            date_str = date_str.split(' ')[0]
        for fmt in ('%d-%b-%y', '%Y-%m-%d', '%d/%m/%Y'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        return None

    def run(self):
        try:
            if self.sheet_type == 'inspection':
                parsed = self._process_inspection()
            elif self.sheet_type == 'rework':
                parsed = self._process_rework()
            elif self.sheet_type == 'appearance':
                parsed = self._process_appearance()
            elif self.sheet_type == 'rework_root_cause':
                parsed = self._process_root_cause()
            else:
                self.error.emit("Unknown sheet type")
                return
            self.finished.emit(True, "Processing completed", parsed)
        except Exception as e:
            self.error.emit(str(e))

    def _process_inspection(self):
        df = self.df.copy()
        date_col = next((c for c in df.columns if 'DATE' in c), None)
        if date_col:
            df['_date'] = df[date_col].apply(self._parse_date)
            df['_date'] = df['_date'].fillna(datetime.now().date())
        else:
            df['_date'] = datetime.now().date()
            self.progress.emit(0, 1)

        # Safe ship column
        if 'SHIP' in df.columns:
            df['_ship'] = df['SHIP'].apply(
                lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.','',1).isdigit() else self._clean_str(x)
            )
        else:
            df['_ship'] = ""

        df['_line'] = df['LINE'].apply(self._clean_str)
        df['_model'] = df['MODEL'].apply(self._clean_str)
        df['_category'] = df['FAULTY'].apply(self._clean_str)
        df['_sub'] = df.get('FAULTY.1', '').apply(self._clean_str) if 'FAULTY.1' in df.columns else ""
        df['_fault_name'] = df.apply(
            lambda r: f"{r['_category']} - {r['_sub']}" if r['_category'] and r['_sub'] else r['_category'] or r['_sub'],
            axis=1
        )
        # Get semi and mmi quantities, treat missing columns as 0
        semi_vals = df['SEMI_TEST'].apply(self._clean_int) if 'SEMI_TEST' in df.columns else 0
        mmi_vals = df['MMI'].apply(self._clean_int) if 'MMI' in df.columns else 0
        # Combine into one total quantity per row
        df['_total_qty'] = semi_vals + mmi_vals

        # Keep only rows where total quantity > 0
        df = df[df['_total_qty'] > 0]
        if df.empty:
            return []

        # Create a single record per fault (not separate for semi/mmi)
        records = []
        for _, row in df.iterrows():
            records.append({
                'date': row['_date'],
                'ship': row['_ship'],
                'line': row['_line'],
                'model': row['_model'],
                'fault_name': row['_fault_name'],
                'source': 'Inspection',   # or keep original station? you can set to 'Semi+MMI'
                'qty': row['_total_qty'],
                'inspection_date': row['_date']
            })
        return records

    def _process_rework(self):
        df = self.df.copy()
        df['date'] = df['RESOLUTION_DATE'].apply(self._parse_date).fillna(datetime.now().date())
        # Safe ship
        if 'SHIP' in df.columns:
            df['ship'] = df['SHIP'].apply(
                lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.','',1).isdigit() else self._clean_str(x)
            )
        else:
            df['ship'] = ""
        df['line'] = df['LINE'].apply(self._clean_str)
        df['model'] = df['MODEL'].apply(self._clean_str)
        df['fault_name'] = df['FAULT_NAME'].apply(self._clean_str)
        df['source_station'] = df['SOURCE_STATION'].apply(self._clean_str)
        df['resolved_qty'] = df['RESOLVED_QTY'].apply(self._clean_int)
        df = df[df['resolved_qty'] > 0]
        records = df[['date','ship','line','model','fault_name','source_station','resolved_qty']].to_dict(orient='records')
        return records

    def _process_appearance(self):
        df = self.df.copy()
        date_col = 'DATE' if 'DATE' in df.columns else None
        if date_col:
            first_date = df[date_col].dropna().iloc[0] if not df[date_col].dropna().empty else None
            sheet_date = self._parse_date(first_date) if first_date is not None else datetime.now().date()
        else:
            sheet_date = datetime.now().date()

        line_col = 'LINE' if 'LINE' in df.columns else None
        model_col = 'MODEL' if 'MODEL' in df.columns else None
        fault_col = 'FAULTY' if 'FAULTY' in df.columns else 'FAULT_NAME'
        qty_col = 'TOTAL' if 'TOTAL' in df.columns else 'APPEARANCE'

        # Safe ship
        if 'SHIP' in df.columns:
            df['ship'] = df['SHIP'].apply(
                lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.','',1).isdigit() else self._clean_str(x)
            )
        else:
            df['ship'] = ""

        df['date'] = sheet_date
        df['line'] = df[line_col].apply(self._clean_str) if line_col else ""
        df['model'] = df[model_col].apply(self._clean_str) if model_col else ""
        df['fault_name'] = df[fault_col].apply(self._clean_str)
        df['qty'] = df[qty_col].apply(self._clean_int)
        df = df[df['qty'] > 0]
        records = df[['date','ship','line','model','fault_name','qty']].to_dict(orient='records')
        for rec in records:
            rec['source'] = 'Appearance Test'
            rec['inspection_date'] = sheet_date
        return records

    def _process_root_cause(self):
        df = self.df.copy()
        df['date'] = df['DATE'].apply(self._parse_date).fillna(datetime.now().date())
        
        # Safe ship
        if 'SHIP' in df.columns:
            df['ship_no'] = df['SHIP'].apply(self._clean_str)
        else:
            df['ship_no'] = ""
        
        df['line'] = df['LINE'].apply(self._clean_str)
        df['model'] = df['MODEL'].apply(self._clean_str)
        df['fault_category'] = df['FAULTY'].apply(self._clean_str)
        df['fault_subcategory'] = df.get('FAULTY.1', '').apply(self._clean_str) if 'FAULTY.1' in df.columns else ""
        
        for col in ['PCBA','MATERIAL','FIXING','SOLDERING']:
            df[col] = df[col].apply(self._clean_int)
        
        df['total_qty'] = df.get('TOTAL', df['PCBA'] + df['MATERIAL'] + df['FIXING'] + df['SOLDERING']).apply(self._clean_int)
        
        # Keep only rows where total_qty > 0
        df = df[df['total_qty'] > 0]
        if df.empty:
            return []
        
        # ========== AGGREGATE BY UNIQUE KEY ==========
        # Group by (date, line, model, fault_category, fault_subcategory)
        grouped = df.groupby(['date', 'line', 'model', 'fault_category', 'fault_subcategory'], as_index=False).agg({
            'ship_no': 'first',   # take first ship (or you could concatenate)
            'PCBA': 'sum',
            'MATERIAL': 'sum',
            'FIXING': 'sum',
            'SOLDERING': 'sum',
            'total_qty': 'sum'
        })
        
        records = []
        for _, row in grouped.iterrows():
            records.append({
                'date': row['date'],
                'ship_no': row['ship_no'],
                'line': row['line'],
                'model': row['model'],
                'fault_category': row['fault_category'],
                'fault_subcategory': row['fault_subcategory'],
                'pcba_qty': row['PCBA'],
                'material_qty': row['MATERIAL'],
                'fixing_qty': row['FIXING'],
                'soldering_qty': row['SOLDERING'],
                'total_qty': row['total_qty']
            })
        return records
# ----------------------------------------------------------------------
# Main ReworkWidget (UI only, launches thread)
# ----------------------------------------------------------------------
class ReworkWidget(QWidget):
    data_saved = pyqtSignal()

    def __init__(self, db: Database, user_data: dict):
        super().__init__()
        self.db = db
        self.user = user_data
        self.current_excel_path = None
        self.parsed_data = []
        self.current_sheet_type = None
        self.setup_ui()
        self.apply_styles()
        self.setMinimumSize(1100, 750)
        self.resize(1300, 850)
        self.ensure_db_schema()
        self.worker = None
        self.thread = None
        self.progress = None

    # ------------------------------------------------------------------
    # UI setup (unchanged from your previous working version)
    # ------------------------------------------------------------------
    def apply_styles(self):
        # ... (paste your existing apply_styles exactly as before)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f4f8;
                font-family: 'Segoe UI', 'Roboto', 'Inter', sans-serif;
            }
            QGroupBox {
                background-color: white;
                border-radius: 20px;
                border: none;
                margin-top: 16px;
                font-weight: bold;
                font-size: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 12px 0 12px;
                color: #1e293b;
            }
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8fafc;
                selection-background-color: #dbeafe;
                gridline-color: #e2e8f0;
                border-radius: 16px;
                border: 1px solid #e2e8f0;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background-color: #dbeafe;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 12px;
                border: none;
                font-weight: 600;
                color: #1e293b;
                font-size: 13px;
            }
            QComboBox {
                padding: 10px;
                border-radius: 10px;
                border: 1px solid #cbd5e1;
                background: white;
                min-width: 180px;
                font-size: 13px;
            }
            QComboBox:focus {
                border: 1px solid #3B82F6;
            }
            QSpinBox {
                padding: 8px;
                border-radius: 8px;
                border: 1px solid #cbd5e1;
                background: white;
                font-size: 13px;
            }
            QDateEdit {
                padding: 8px 12px;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background: white;
                font-size: 13px;
                color: #1e293b;
                min-width: 140px;
            }
            QDateEdit:focus {
                border-color: #3B82F6;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 20px;
                border-left: 1px solid #cbd5e1;
            }
            QDateEdit::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #64748b;
                margin-right: 6px;
            }
            QCalendarWidget {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
            QCalendarWidget QToolButton {
                color: #1e293b;
                background: #f8fafc;
                border: none;
                border-radius: 4px;
            }
            QLabel {
                color: #334155;
                font-size: 13px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

    def setup_ui(self):
        # ... (paste your existing setup_ui exactly as before)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        container = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)
        container.setLayout(main_layout)
        scroll.setWidget(container)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(scroll)
        self.layout().setContentsMargins(0, 0, 0, 0)

        header_frame = QFrame()
        header_frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0f172a, stop:1 #1e293b);
            border-radius: 24px;
            padding: 16px 24px;
        """)
        header_layout = QHBoxLayout()
        header_label = QLabel("📥 IMPORT DATA (Excel)")
        header_label.setStyleSheet("color: white; font-size: 22px; font-weight: 700;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_frame.setLayout(header_layout)
        main_layout.addWidget(header_frame)

        self.step1_group = self.create_step_group("1️⃣ SELECT EXCEL FILE")
        self.setup_file_selection(self.step1_group)
        main_layout.addWidget(self.step1_group)

        self.step2_group = self.create_step_group("2️⃣ REVIEW & EDIT DATA")
        self.setup_data_table(self.step2_group)
        self.step2_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.step2_group, stretch=1)

        self.total_count_label = QLabel("📊 Total Records: 0")
        self.total_count_label.setStyleSheet("""
            QLabel {
                font-weight: 600;
                color: #1e293b;
                padding: 8px 12px;
                background: #f1f5f9;
                border-radius: 10px;
            }
        """)
        main_layout.addWidget(self.total_count_label)

        self.step3_group = self.create_step_group("3️⃣ SAVE TO DATABASE")
        self.setup_action_buttons(self.step3_group)
        main_layout.addWidget(self.step3_group)

        self.status_label = QLabel("✅ Ready. Please load an Excel file.")
        self.status_label.setStyleSheet("""
            QLabel {
                background: #f0fdf4;
                color: #10B981;
                padding: 12px 16px;
                border-radius: 12px;
                font-weight: 500;
                font-size: 13px;
                border: 1px solid #bbf7d0;
            }
        """)
        main_layout.addWidget(self.status_label)

    def create_step_group(self, title):
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                background: white;
                border-radius: 20px;
                margin-top: 12px;
                padding-top: 16px;
                border: 1px solid #e2e8f0;
            }
            QGroupBox::title {
                left: 20px;
                padding: 0 12px;
                color: #0f172a;
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        group.setLayout(layout)
        return group

    def setup_file_selection(self, group):
        layout = group.layout()
        class DropLabel(QLabel):
            def dragEnterEvent(self, e):
                if e.mimeData().hasUrls():
                    urls = e.mimeData().urls()
                    if urls and urls[0].toLocalFile().lower().endswith(('.xlsx', '.xls')):
                        e.acceptProposedAction()
                        self.setStyleSheet("border: 2px solid #10B981; background: #ecfdf5; border-radius: 20px; padding: 28px;")
                    else:
                        e.ignore()
            def dragLeaveEvent(self, e):
                self.setStyleSheet("border: 2px dashed #cbd5e0; background: #fafafa; border-radius: 20px; padding: 28px;")
            def dropEvent(self, e):
                self.setStyleSheet("border: 2px dashed #cbd5e0; background: #fafafa; border-radius: 20px; padding: 28px;")
                file_path = e.mimeData().urls()[0].toLocalFile()
                self.parent_widget.load_excel_file(file_path)
        self.drop_label = DropLabel("📂 Drag & Drop Excel file here\n      or click Browse")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("border: 2px dashed #cbd5e0; background: #fafafa; border-radius: 20px; padding: 28px; color: #64748b; font-size: 14px;")
        self.drop_label.setAcceptDrops(True)
        self.drop_label.parent_widget = self
        layout.addWidget(self.drop_label)

        row = QHBoxLayout()
        self.browse_btn = ModernButton("📂 Browse", "#3B82F6")
        self.browse_btn.clicked.connect(self.browse_excel_file)
        row.addWidget(self.browse_btn)
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        row.addWidget(self.file_label)
        row.addStretch()
        layout.addLayout(row)

        sheet_row = QHBoxLayout()
        sheet_row.addWidget(QLabel("📄 Sheet:"))
        self.sheet_combo = QComboBox()
        self.sheet_combo.setEnabled(False)
        self.sheet_combo.currentIndexChanged.connect(self.on_sheet_selected)
        sheet_row.addWidget(self.sheet_combo)
        sheet_row.addStretch()
        layout.addLayout(sheet_row)

    def setup_data_table(self, group):
        layout = group.layout()
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setMinimumHeight(450)
        self.data_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.data_table.setSortingEnabled(True)
        self.data_table.verticalHeader().setVisible(False)
        self.data_table.setWordWrap(True)
        self.data_table.setShowGrid(False)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.data_table)

    def setup_action_buttons(self, group):
        layout = group.layout()
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        self.save_btn = ModernButton("💾 SAVE TO DATABASE", "#10B981")
        self.save_btn.clicked.connect(self.save_to_database)
        btn_layout.addWidget(self.save_btn)
        self.clear_btn = ModernButton("🗑 CLEAR TABLE", "#ef4444")
        self.clear_btn.clicked.connect(self.clear_table)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def browse_excel_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)")
        if file_path:
            self.load_excel_file(file_path)

    def load_excel_file(self, file_path):
        if not PANDAS_AVAILABLE:
            CustomMessageBox.show_error(self, "Missing Dependency", "pandas not installed. Run: pip install pandas openpyxl")
            return
        try:
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names
            if not sheet_names:
                raise ValueError("No sheets found.")
            self.current_excel_path = file_path
            self.file_label.setText(f"📁 {os.path.basename(file_path)}")
            self.sheet_combo.clear()
            self.sheet_combo.addItems(sheet_names)
            self.sheet_combo.setEnabled(True)
            self.status_label.setText(f"✅ File loaded: {os.path.basename(file_path)}. Select a sheet to parse.")
        except Exception as e:
            CustomMessageBox.show_error(self, "Error", f"Could not read file:\n{str(e)}")
            self.sheet_combo.setEnabled(False)
            self.file_label.setText("No file selected")
            self.status_label.setText("❌ Failed to load file.")

    def on_sheet_selected(self, index):
        if index >= 0 and self.current_excel_path:
            sheet_name = self.sheet_combo.currentText()
            self.status_label.setText(f"🔄 Parsing sheet '{sheet_name}'...")
            self.parse_and_display_sheet(sheet_name)

    # ------------------------------------------------------------------
    # Parse in thread
    # ------------------------------------------------------------------
    def parse_and_display_sheet(self, sheet_name):
        try:
            df = pd.read_excel(self.current_excel_path, sheet_name=sheet_name)
            df.columns = [str(col).strip().upper().replace(' ', '_') for col in df.columns]

            # Detect sheet type
            if {'PCBA', 'MATERIAL', 'FIXING', 'SOLDERING'}.issubset(df.columns):
                sheet_type = 'rework_root_cause'
            elif {'LINE', 'MODEL', 'FAULTY', 'SEMI_TEST', 'MMI'}.issubset(df.columns):
                sheet_type = 'inspection'
            elif {'LINE', 'MODEL', 'FAULT_NAME', 'SOURCE_STATION', 'RESOLVED_QTY', 'RESOLUTION_DATE'}.issubset(df.columns):
                sheet_type = 'rework'
            elif {'DATE', 'LINE', 'MODEL', 'FAULTY', 'TOTAL'}.issubset(df.columns):
                sheet_type = 'appearance'
            elif {'LINE', 'MODEL', 'FAULT_NAME', 'APPEARANCE'}.issubset(df.columns):
                sheet_type = 'appearance'
            else:
                CustomMessageBox.show_warning(self, "Invalid Format", f"Sheet '{sheet_name}' does not match known formats.")
                self.clear_table()
                return

            self.current_sheet_type = sheet_type
            self.progress = QProgressDialog(f"Processing {sheet_type} sheet...", "Cancel", 0, 100, self)
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setCancelButton(None)
            self.progress.show()
            QApplication.processEvents()

            # Start worker thread
            self.thread = QThread()
            self.worker = ProcessWorker(sheet_type, df, self.user)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.on_processing_finished)
            self.worker.error.connect(self.on_processing_error)
            self.worker.progress.connect(self.update_progress)
            self.thread.start()

        except Exception as e:
            CustomMessageBox.show_error(self, "Error", str(e))
            self.clear_table()

    def update_progress(self, current, total):
        if self.progress:
            self.progress.setValue(int(current / total * 100))

    def on_processing_finished(self, success, message, parsed_data):
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        if self.progress:
            self.progress.close()
        if success:
            self.parsed_data = parsed_data
            # Update UI based on sheet type
            if self.current_sheet_type == 'inspection':
                self.step2_group.setTitle("2️⃣ REVIEW INSPECTION FAULTS")
                total_qty = sum(f['qty'] for f in self.parsed_data)
                self.total_count_label.setText(f"📊 Total Fault Entries: {len(self.parsed_data)} | Total Quantity: {total_qty}")
            elif self.current_sheet_type == 'rework':
                self.step2_group.setTitle("2️⃣ REVIEW REWORK COMPLETIONS")
                total_qty = sum(r['resolved_qty'] for r in self.parsed_data)
                self.total_count_label.setText(f"📊 Total Rework Records: {len(self.parsed_data)} | Total Resolved Qty: {total_qty}")
            elif self.current_sheet_type == 'appearance':
                self.step2_group.setTitle("2️⃣ REVIEW APPEARANCE FAULTS")
                total_qty = sum(a['qty'] for a in self.parsed_data)
                self.total_count_label.setText(f"📊 Total Appearance Faults: {len(self.parsed_data)} | Total Quantity: {total_qty}")
            elif self.current_sheet_type == 'rework_root_cause':
                self.step2_group.setTitle("2️⃣ REVIEW REWORK ROOT CAUSE BREAKDOWN")
                total_qty = sum(r['total_qty'] for r in self.parsed_data)
                self.total_count_label.setText(f"📊 Total Rework Actions: {len(self.parsed_data)} | Total Units: {total_qty}")
            # Populate table
            if self.current_sheet_type in ('inspection', 'appearance'):
                self.populate_inspection_table()
            elif self.current_sheet_type == 'rework':
                self.populate_rework_table()
            elif self.current_sheet_type == 'rework_root_cause':
                self.populate_root_cause_table()
            self.status_label.setText(f"✅ Loaded {len(self.parsed_data)} records.")
        else:
            CustomMessageBox.show_error(self, "Processing Error", message)

    def on_processing_error(self, err_msg):
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        if self.progress:
            self.progress.close()
        CustomMessageBox.show_error(self, "Processing Error", err_msg)
        self.clear_table()
        
    # ------------------------------------------------------------------
    # Table population methods (unchanged – reuse your existing ones)
    # ------------------------------------------------------------------
    def _center_item(self, item):
        if item:
            item.setTextAlignment(Qt.AlignCenter)

    def populate_inspection_table(self):
        # Same as your existing populate_inspection_table
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(["Date", "Ship", "Line", "Model", "Fault Name", "Source", "Qty"])
        self.data_table.setRowCount(len(self.parsed_data))
        self.spinboxes = []
        for row, fault in enumerate(self.parsed_data):
            item_date = QTableWidgetItem(fault['date'].strftime('%Y-%m-%d')); self._center_item(item_date); self.data_table.setItem(row, 0, item_date)
            item_ship = QTableWidgetItem(fault.get('ship', '')); self._center_item(item_ship); self.data_table.setItem(row, 1, item_ship)
            item_line = QTableWidgetItem(fault['line']); self._center_item(item_line); self.data_table.setItem(row, 2, item_line)
            item_model = QTableWidgetItem(fault['model']); self._center_item(item_model); self.data_table.setItem(row, 3, item_model)
            item_fault = QTableWidgetItem(fault['fault_name']); self._center_item(item_fault); self.data_table.setItem(row, 4, item_fault)
            item_source = QTableWidgetItem(fault['source']); self._center_item(item_source); self.data_table.setItem(row, 5, item_source)
            spin = QSpinBox()
            spin.setRange(0, 9999)
            spin.setValue(fault['qty'])
            spin.setAlignment(Qt.AlignCenter)
            spin.valueChanged.connect(lambda val, r=row: self.update_inspection_quantity(r, val))
            self.data_table.setCellWidget(row, 6, spin)
            self.spinboxes.append(spin)
        self.data_table.resizeRowsToContents()
        widths = [90, 60, 80, 120, 0, 100, 80]
        for col, w in enumerate(widths):
            if w > 0:
                self.data_table.setColumnWidth(col, w)
        self.data_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

    def populate_rework_table(self):
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(["Date", "Ship", "Line", "Model", "Fault Name", "Source", "Resolved Qty"])
        self.data_table.setRowCount(len(self.parsed_data))
        for row, rec in enumerate(self.parsed_data):
            item_date = QTableWidgetItem(rec['date'].strftime('%Y-%m-%d')); self._center_item(item_date); self.data_table.setItem(row, 0, item_date)
            item_ship = QTableWidgetItem(rec.get('ship', '')); self._center_item(item_ship); self.data_table.setItem(row, 1, item_ship)
            item_line = QTableWidgetItem(rec['line']); self._center_item(item_line); self.data_table.setItem(row, 2, item_line)
            item_model = QTableWidgetItem(rec['model']); self._center_item(item_model); self.data_table.setItem(row, 3, item_model)
            item_fault = QTableWidgetItem(rec['fault_name']); self._center_item(item_fault); self.data_table.setItem(row, 4, item_fault)
            item_source = QTableWidgetItem(rec['source_station']); self._center_item(item_source); self.data_table.setItem(row, 5, item_source)
            qty_item = QTableWidgetItem(str(rec['resolved_qty'])); self._center_item(qty_item); self.data_table.setItem(row, 6, qty_item)
        self.data_table.resizeRowsToContents()
        widths = [90, 60, 80, 120, 0, 100, 80]
        for col, w in enumerate(widths):
            if w > 0:
                self.data_table.setColumnWidth(col, w)
        self.data_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

    def populate_root_cause_table(self):
        self.data_table.setColumnCount(11)
        self.data_table.setHorizontalHeaderLabels([
            "Date", "Ship", "Line", "Model", "Fault Category",
            "Sub Fault", "PCBA", "Material", "Fixing", "Soldering", "Total"
        ])
        self.data_table.setRowCount(len(self.parsed_data))
        for row, rec in enumerate(self.parsed_data):
            item_date = QTableWidgetItem(rec['date'].strftime('%Y-%m-%d')); self._center_item(item_date); self.data_table.setItem(row, 0, item_date)
            item_ship = QTableWidgetItem(rec['ship_no']); self._center_item(item_ship); self.data_table.setItem(row, 1, item_ship)
            item_line = QTableWidgetItem(rec['line']); self._center_item(item_line); self.data_table.setItem(row, 2, item_line)
            item_model = QTableWidgetItem(rec['model']); self._center_item(item_model); self.data_table.setItem(row, 3, item_model)
            item_cat = QTableWidgetItem(rec['fault_category']); self._center_item(item_cat); self.data_table.setItem(row, 4, item_cat)
            item_sub = QTableWidgetItem(rec['fault_subcategory']); self._center_item(item_sub); self.data_table.setItem(row, 5, item_sub)
            item_pcba = QTableWidgetItem(str(rec['pcba_qty'])); self._center_item(item_pcba); self.data_table.setItem(row, 6, item_pcba)
            item_mat = QTableWidgetItem(str(rec['material_qty'])); self._center_item(item_mat); self.data_table.setItem(row, 7, item_mat)
            item_fix = QTableWidgetItem(str(rec['fixing_qty'])); self._center_item(item_fix); self.data_table.setItem(row, 8, item_fix)
            item_sol = QTableWidgetItem(str(rec['soldering_qty'])); self._center_item(item_sol); self.data_table.setItem(row, 9, item_sol)
            item_total = QTableWidgetItem(str(rec['total_qty'])); self._center_item(item_total); self.data_table.setItem(row, 10, item_total)
        self.data_table.resizeRowsToContents()
        widths = [90, 70, 80, 120, 150, 150, 70, 70, 70, 70, 80]
        for col, w in enumerate(widths):
            self.data_table.setColumnWidth(col, w)
        self.data_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.data_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

    def update_inspection_quantity(self, row, value):
        if row < len(self.parsed_data) and 'qty' in self.parsed_data[row]:
            self.parsed_data[row]['qty'] = value
            total = sum(f['qty'] for f in self.parsed_data if 'qty' in f)
            self.total_count_label.setText(f"📊 Total Fault Entries: {len(self.parsed_data)} | Total Quantity: {total}")

    def clear_table(self):
        self.data_table.setRowCount(0)
        self.data_table.setColumnCount(0)
        self.parsed_data = []
        self.spinboxes = []
        self.current_sheet_type = None
        self.total_count_label.setText("📊 Total Records: 0")
        self.status_label.setText("✅ Table cleared. Load a file to start.")
        self.step2_group.setTitle("2️⃣ REVIEW & EDIT DATA")

    # ------------------------------------------------------------------
    # Save methods – also run in thread (to avoid UI freeze)
    # ------------------------------------------------------------------
    def save_to_database(self):
        if not self.parsed_data:
            CustomMessageBox.show_warning(self, "No Data", "No data loaded.")
            return

        # Create a custom dialog with indeterminate progress bar
        self.loading_dialog = QDialog(self)
        self.loading_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.loading_dialog.setAttribute(Qt.WA_TranslucentBackground)
        self.loading_dialog.setFixedSize(400, 120)
        layout = QVBoxLayout(self.loading_dialog)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("Saving data to database...")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #1e293b; font-size: 14px; font-weight: bold;")
        layout.addWidget(label)

        # Indeterminate progress bar (moving line)
        progress = QProgressBar()
        progress.setRange(0, 0)  # 0,0 makes it indeterminate (moving line)
        progress.setFixedHeight(8)
        progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #e2e8f0;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 4px;
            }
        """)
        layout.addWidget(progress)

        self.loading_dialog.show()
        QApplication.processEvents()

        # Run save in background thread
        self.thread = QThread()
        self.save_worker = SaveWorker(self.current_sheet_type, self.parsed_data, self.db, self.user)
        self.save_worker.moveToThread(self.thread)
        self.thread.started.connect(self.save_worker.run)
        self.save_worker.finished.connect(self.on_save_finished)
        self.save_worker.error.connect(self.on_save_error)
        self.thread.start()
        
    def on_save_finished(self, success, message, inserted, updated):
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        if hasattr(self, 'loading_dialog') and self.loading_dialog:
            self.loading_dialog.accept()
            self.loading_dialog = None
        if success:
            CustomMessageBox.show_success(self, "Import Complete", f"✅ Inserted: {inserted}, Updated: {updated}")
            self.clear_table()
            self.data_saved.emit()
        else:
            CustomMessageBox.show_error(self, "Save Error", message)

    def on_save_error(self, err_msg):
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        if hasattr(self, 'loading_dialog') and self.loading_dialog:
            self.loading_dialog.accept()
            self.loading_dialog = None
        CustomMessageBox.show_error(self, "Save Error", err_msg)

    def ensure_db_schema(self):
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    IF EXISTS (SELECT * FROM syscolumns WHERE name='product_id' AND id=OBJECT_ID('inspections') AND isnullable=0)
                    ALTER TABLE inspections ALTER COLUMN product_id INT NULL
                """)
                for table in ['inspections', 'rework_completed']:
                    cursor.execute(f"""
                        IF NOT EXISTS (SELECT * FROM syscolumns WHERE name='ship' AND id=OBJECT_ID('{table}'))
                        ALTER TABLE {table} ADD ship NVARCHAR(50) NULL
                    """)
                conn.commit()
        except Exception as e:
            print(f"Schema update warning: {e}")

    def refresh(self):
        pass


# ----------------------------------------------------------------------
# Save Worker Thread
# ----------------------------------------------------------------------
class SaveWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str, int, int)
    error = pyqtSignal(str)

    def __init__(self, sheet_type, parsed_data, db, user):
        super().__init__()
        self.sheet_type = sheet_type
        self.parsed_data = parsed_data
        self.db = db
        self.user = user

    def run(self):
        try:
            if self.sheet_type == 'inspection' or self.sheet_type == 'appearance':
                inserted, updated = self._save_inspection()
            elif self.sheet_type == 'rework':
                inserted, updated = self._save_rework()
            elif self.sheet_type == 'rework_root_cause':
                inserted, updated = self._save_root_cause()
            else:
                self.error.emit("Unknown sheet type")
                return
            self.finished.emit(True, "Save completed", inserted, updated)
        except Exception as e:
            self.error.emit(str(e))

    def _save_inspection(self):
        # Group by (line, model, station)
        grouped = {}
        for f in self.parsed_data:
            if f['qty'] <= 0:
                continue
            key = (f['line'], f['model'], f['source'])
            grouped.setdefault(key, []).append(f)

        inspection_date = self.parsed_data[0].get('inspection_date', datetime.now().date())
        inspector_id = int(self.user.get('id', 1))
        inspector_name = self.user.get('full_name', 'Inspector')
        inspection_list = []
        for (line, model, station), faults in grouped.items():
            ship = faults[0].get('ship', '')
            defects_lines = [f"{f['fault_name']}: {f['qty']} pcs" for f in faults]
            total_rejected = sum(f['qty'] for f in faults)
            defects_text = "\n".join(defects_lines)
            remarks = f"Imported from Excel on {datetime.now()} | Ship: {ship} | Line: {line} | Model: {model} | Inspector: {inspector_name}"
            inspection_list.append({
                'ship': ship,
                'line': line,
                'floor': 'N/A',
                'station': station,
                'defects': defects_text,
                'rejected_qty': total_rejected,
                'remarks': remarks
            })

        # Duplicate check
        existing_map = {}
        for insp in inspection_list:
            existing = self.db.execute_query(
                "SELECT id FROM inspections WHERE CAST(inspection_date AS DATE)=? AND line=? AND inspection_type=?",
                (inspection_date, insp['line'], insp['station']), fetch_one=True)
            if existing:
                existing_map[(insp['line'], insp['station'])] = existing['id']

        replace = False
        if existing_map:
            # In a worker thread, we cannot show a GUI dialog directly.
            # For simplicity, we replace by default. To let user choose, you would need to communicate with main thread.
            # Here we choose 'replace' – because the user is re‑importing a corrected file.
            replace = True

        inserted = updated = 0
        for insp in inspection_list:
            key = (insp['line'], insp['station'])
            if replace and key in existing_map:
                self.db.execute_query("""
                    UPDATE inspections 
                    SET ship=?, defects=?, rejected_quantity=?, remarks=?, updated_at=GETDATE()
                    WHERE id=?
                """, (insp['ship'], insp['defects'], insp['rejected_qty'], insp['remarks'], existing_map[key]))
                updated += 1
            else:
                code = f"IMP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{insp['station'][:3]}-{uuid.uuid4().hex[:6]}"
                with self.db.get_connection() as conn:
                    conn.cursor().execute("""
                        INSERT INTO inspections 
                        (inspection_code, product_id, inspector_id, inspection_type, inspection_date,
                        quantity_checked, accepted_quantity, rejected_quantity, quality_score,
                        defects, remarks, status, line, floor, ship)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (code, None, inspector_id, insp['station'], inspection_date,
                          insp['rejected_qty'], 0, insp['rejected_qty'], 0.0,
                          insp['defects'], insp['remarks'], 'Completed', insp['line'], insp['floor'], insp['ship']))
                    inserted += 1
        return inserted, updated

    def _save_rework(self):
        inserted = updated = 0
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for rec in self.parsed_data:
                cursor.execute("""
                    SELECT id FROM rework_completed
                    WHERE resolution_date = ? AND line = ? AND model = ? AND fault_name = ? AND source_station = ? AND ship = ?
                """, (rec['date'], rec['line'], rec['model'], rec['fault_name'], rec['source_station'], rec.get('ship', '')))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute("""
                        UPDATE rework_completed
                        SET resolved_qty = ?, remarks = ?, imported_at = GETDATE()
                        WHERE id = ?
                    """, (rec['resolved_qty'], f"Updated on {datetime.now()}", existing[0]))
                    updated += 1
                else:
                    cursor.execute("""
                        INSERT INTO rework_completed (line, model, fault_name, source_station, resolved_qty, resolution_date, remarks, ship)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (rec['line'], rec['model'], rec['fault_name'], rec['source_station'],
                          rec['resolved_qty'], rec['date'], f"Imported on {datetime.now()}", rec.get('ship', '')))
                    inserted += 1
            conn.commit()
        return inserted, updated

    def _save_root_cause(self):
        inserted = updated = 0
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for rec in self.parsed_data:
                cursor.execute("""
                    SELECT id FROM rework_root_cause
                    WHERE record_date = ? AND line = ? AND model = ? 
                      AND fault_category = ? AND fault_subcategory = ?
                """, (rec['date'], rec['line'], rec['model'], rec['fault_category'], rec['fault_subcategory']))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute("""
                        UPDATE rework_root_cause
                        SET pcba_qty = ?, material_qty = ?, fixing_qty = ?, soldering_qty = ?,
                            total_qty = ?, remarks = ?, imported_at = GETDATE()
                        WHERE id = ?
                    """, (rec['pcba_qty'], rec['material_qty'], rec['fixing_qty'], rec['soldering_qty'],
                          rec['total_qty'], f"Updated on {datetime.now()}", existing[0]))
                    updated += 1
                else:
                    cursor.execute("""
                        INSERT INTO rework_root_cause 
                        (ship_no, record_date, line, model, fault_category, fault_subcategory,
                         pcba_qty, material_qty, fixing_qty, soldering_qty, total_qty, remarks)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (rec['ship_no'], rec['date'], rec['line'], rec['model'],
                          rec['fault_category'], rec['fault_subcategory'],
                          rec['pcba_qty'], rec['material_qty'], rec['fixing_qty'], rec['soldering_qty'],
                          rec['total_qty'], f"Imported on {datetime.now()}"))
                    inserted += 1
            conn.commit()
        return inserted, updated


# ----------------------------------------------------------------------
# Dummy ModernButton class (keep as is)
# ----------------------------------------------------------------------
class ModernButton(QPushButton):
    def __init__(self, text, color="#3B82F6", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}, stop:1 {self._lighten_color(color, 10)});
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self._darken_color(color, 5)}, stop:1 {color});
            }}
            QPushButton:pressed {{
                background: {self._darken_color(color, 15)};
            }}
        """)

    def _darken_color(self, color, percent=10):
        if color.startswith('#'):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = max(0, r - int(r * percent / 100))
            g = max(0, g - int(g * percent / 100))
            b = max(0, b - int(b * percent / 100))
            return f"#{r:02x}{g:02x}{b:02x}"
        return color

    def _lighten_color(self, color, percent=10):
        if color.startswith('#'):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = min(255, r + int((255 - r) * percent / 100))
            g = min(255, g + int((255 - g) * percent / 100))
            b = min(255, b + int((255 - b) * percent / 100))
            return f"#{r:02x}{g:02x}{b:02x}"
        return color

    pass