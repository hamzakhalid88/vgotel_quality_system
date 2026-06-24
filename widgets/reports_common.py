# widgets/reports_common.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from database import Database
from custom_dialogs import CustomMessageBox

# ----------------------------------------------------------------------
# Model Aliases and helpers
# ----------------------------------------------------------------------
MODEL_ALIASES = {
    "IMUSIC": ["I MUSIC", "IMUSIC", "I MUSIC", "I MUSIC", "I-MUSIC", "I-MUSIC "],
    "IMUSIC PLUS": ["I MUSIC PLUS", "IMUSIC PLUS", "I-MUSIC PLUS", "I MUSIC+", "IMUSIC+"],
    "IMUSIC PRO": ["I MUSIC PRO", "IMUSIC PRO", "I-MUSIC PRO", "IMUSICPRO", "I MUSICPRO"],
    "EASY200 LITE": ["EASY200 LITE", "EASY 200 LITE", "EASY200LITE", "EASY 200LITE", "EASY200-LITE", "EASY 200-LITE"],
    "SMT": ["SMT", "S.M.T", "S M T"],
    "PCBA": ["PCBA", "P.C.B.A", "PCB ASSEMBLY"],
}

def normalize_model(raw):
    """Normalize model name using aliases - CASE INSENSITIVE."""
    if not raw:
        return raw
    raw_clean = raw.strip().upper()
    for canonical, variants in MODEL_ALIASES.items():
        if raw_clean in [v.upper() for v in variants]:
            return canonical
    return raw.strip()

def get_variants(canonical):
    """Get all variants for a canonical model name."""
    for canonical_name, variants in MODEL_ALIASES.items():
        if canonical_name.upper() == canonical.upper():
            return variants
    return [canonical]

def get_all_model_variants():
    """Get flat list of all known model aliases for SQL IN clauses."""
    all_vars = []
    for variants in MODEL_ALIASES.values():
        all_vars.extend(variants)
    return list(set(all_vars))

# ----------------------------------------------------------------------
# RootCauseDialog
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

        header = QLabel("🔧 Root Cause Mapping")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        layout.addWidget(header)

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

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

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
        root_cause = self.root_cause_input.toPlainText().strip()
        responsible = self.responsible_input.text().strip()
        solution = self.solution_input.toPlainText().strip()

        try:
            with self.db.get_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT id FROM rework_resolution_mapping 
                    WHERE LOWER(LTRIM(RTRIM(fault_category))) = LOWER(LTRIM(RTRIM(?))) 
                    AND LOWER(LTRIM(RTRIM(COALESCE(fault_subcategory, '')))) = LOWER(LTRIM(RTRIM(COALESCE(?, ''))))
                """, (self.fault_category, self.fault_subcategory or ''))
                existing = c.fetchone()
                if existing:
                    c.execute("""
                        UPDATE rework_resolution_mapping 
                        SET root_cause = ?, responsible_dept = ?, solution_plan = ?, updated_at = GETDATE()
                        WHERE id = ?
                    """, (root_cause, responsible, solution, existing[0]))
                else:
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


# ----------------------------------------------------------------------
# FaultDetailsDialog
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
        self.setStyleSheet("background-color: #f8fafc;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20,20,20,20)

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
                if qty >= 30:
                    qty_item.setForeground(QColor("#991b1b"))
                    qty_item.setBackground(QColor("#fee2e2"))
                elif qty >= 20:
                    qty_item.setForeground(QColor("#9a3412"))
                    qty_item.setBackground(QColor("#ffedd5"))
                elif qty >= 10:
                    qty_item.setForeground(QColor("#b45309"))
                    qty_item.setBackground(QColor("#fef3c7"))
                elif qty >= 5:
                    qty_item.setForeground(QColor("#d97706"))
                    qty_item.setBackground(QColor("#fffbeb"))
                elif qty > 0:
                    qty_item.setForeground(QColor("#15803d"))
                    qty_item.setBackground(QColor("#dcfce7"))
                else:
                    qty_item.setForeground(QColor("#64748b"))
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