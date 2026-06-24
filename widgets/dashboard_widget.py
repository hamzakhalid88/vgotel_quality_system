from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QTableWidget, QTableWidgetItem,
    QProgressBar, QGraphicsDropShadowEffect, QPushButton,
    QScrollArea, QHeaderView, QSizePolicy, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont, QColor
from database import Database
import re
from datetime import datetime


class ModernButton(QPushButton):
    def __init__(self, text, color="#4A90E2", icon=""):
        super().__init__(text)
        self.color = color
        self.icon_text = icon
        self.setup_ui()
        
    def setup_ui(self):
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self.color};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 13px;
                font-family: 'Segoe UI';
            }}
            QPushButton:hover {{ background: {self.adjust_color(self.color, -20)}; }}
            QPushButton:pressed {{ background: {self.adjust_color(self.color, -40)}; }}
        """)
        if self.icon_text:
            self.setText(f"{self.icon_text}  {self.text()}")
    
    def adjust_color(self, color, amount):
        color = color.lstrip('#')
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))
        return f"#{r:02x}{g:02x}{b:02x}"


class StatsCard(QFrame):
    def __init__(self, title, value="0", icon="📊", color="#4A90E2", trend=None):
        super().__init__()
        self.title = title
        self.value = value
        self.icon = icon
        self.color = color
        self.trend = trend
        self.setup_ui()
        
    def setup_ui(self):
        self.setObjectName("stats_card")
        self.setStyleSheet(f"""
            #stats_card {{
                background: white;
                border-radius: 16px;
                border: 1px solid #E5E8EC;
            }}
        """)
        self.setMinimumHeight(140)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 15))
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        top_layout = QHBoxLayout()
        icon_container = QLabel(self.icon)
        icon_container.setStyleSheet(f"background: {self.color}10; padding: 8px; border-radius: 10px; font-size: 20px;")
        top_layout.addWidget(icon_container)
        top_layout.addStretch()
        if self.trend:
            trend_label = QLabel(self.trend)
            trend_color = "#50C878" if "↑" in self.trend else "#FF6B6B"
            trend_label.setStyleSheet(f"color: {trend_color}; font-size: 12px; font-weight: 600;")
            top_layout.addWidget(trend_label)
        layout.addLayout(top_layout)
        
        self.value_label = QLabel(self.value)
        self.value_label.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {self.color}; font-family: 'Segoe UI';")
        layout.addWidget(self.value_label)
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet("color: #6B7280; font-size: 13px; font-weight: 500; letter-spacing: 0.3px;")
        layout.addWidget(title_label)
        
    def setValue(self, value, suffix=""):
        try:
            val = float(value) if value is not None else 0
            if suffix == "%":
                self.value_label.setText(f"{val:.1f}{suffix}")
            else:
                self.value_label.setText(f"{int(val):,}")
        except:
            self.value_label.setText(f"0{suffix}")


class DashboardWidget(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.current_model_filter = "All Models"
        self.full_data = []          # store current dataset
        self.setup_ui()
        self.refresh_data()
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(30000)      # refresh every 30 seconds

    # ---------- UI Setup ----------
    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        navbar = self.create_navbar()
        main_layout.addWidget(navbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: #F5F7FA; }")

        container = QWidget()
        container.setStyleSheet("background: #F5F7FA;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)
        container.setLayout(content_layout)

        # Welcome card
        welcome_card = self.create_welcome_section()
        content_layout.addWidget(welcome_card)

        # Model filter
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        filter_label = QLabel("📌 Select Model:")
        filter_label.setStyleSheet("font-weight: bold; color: #1F2937;")
        filter_layout.addWidget(filter_label)

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        self.model_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #E5E8EC;
                border-radius: 8px;
                background: white;
                font-size: 13px;
            }
            QComboBox::drop-down { border: none; }
        """)
        self.model_combo.addItem("All Models")
        self.model_combo.currentTextChanged.connect(self.on_model_filter_changed)
        filter_layout.addWidget(self.model_combo)
        filter_layout.addStretch()
        content_layout.addLayout(filter_layout)

        # Line summary
        line_summary_label = QLabel("📊 Line-wise Fault & Repair Summary (Selected Model)")
        line_summary_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937; margin-top: 10px;")
        content_layout.addWidget(line_summary_label)

        self.line_cards_layout = QGridLayout()
        self.line_cards_layout.setSpacing(20)
        content_layout.addLayout(self.line_cards_layout)

        # Model table
        model_report_label = QLabel("📋 Model-wise Fault & Repair Report (All Models)")
        model_report_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937; margin-top: 10px;")
        content_layout.addWidget(model_report_label)

        self.model_table = QTableWidget()
        self.model_table.setColumnCount(7)
        self.model_table.setHorizontalHeaderLabels(["Model", "Line", "Semi Faults", "MMI Faults", "Total Faults", "Repairs", "Unresolved"])
        self.model_table.setMinimumHeight(400)
        self.model_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.model_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #E5E8EC; border-radius: 16px; }
            QTableWidget::item { padding: 12px 15px; border-bottom: 1px solid #F0F0F0; color: #1F2937; font-size: 13px; }
            QHeaderView::section { background: #FAFBFC; padding: 12px 15px; font-weight: 600; color: #6B7280; font-size: 12px; }
        """)
        self.model_table.horizontalHeader().setStretchLastSection(True)
        self.model_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.model_table.setAlternatingRowColors(True)
        self.model_table.setShowGrid(False)
        self.model_table.verticalHeader().setVisible(False)
        self.model_table.setEditTriggers(QTableWidget.NoEditTriggers)
        content_layout.addWidget(self.model_table)

        # Quick actions
        actions_card = self.create_quick_actions()
        content_layout.addWidget(actions_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def create_navbar(self):
        navbar = QFrame()
        navbar.setStyleSheet("QFrame { background: white; border-bottom: 1px solid #E5E8EC; }")
        navbar.setFixedHeight(70)
        layout = QHBoxLayout()
        layout.setContentsMargins(30, 0, 30, 0)
        navbar.setLayout(layout)
        brand = QLabel("🏭 Quality Management System")
        brand.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        layout.addWidget(brand)
        layout.addStretch()
        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #6B7280; font-size: 13px;")
        self.update_time()
        time_timer = QTimer()
        time_timer.timeout.connect(self.update_time)
        time_timer.start(1000)
        layout.addWidget(self.time_label)
        user_badge = QFrame()
        user_badge.setStyleSheet("background: #F3F4F6; border-radius: 25px; padding: 8px 16px;")
        user_layout = QHBoxLayout()
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_badge.setLayout(user_layout)
        user_icon = QLabel("👤")
        user_icon.setStyleSheet("font-size: 14px;")
        user_layout.addWidget(user_icon)
        user_name = QLabel("Admin")
        user_name.setStyleSheet("color: #1F2937; font-weight: 500; font-size: 13px;")
        user_layout.addWidget(user_name)
        layout.addWidget(user_badge)
        return navbar

    def create_welcome_section(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4A90E2, stop:1 #667EEA); border-radius: 20px; }
        """)
        card.setFixedHeight(120)
        layout = QHBoxLayout()
        layout.setContentsMargins(30, 0, 30, 0)
        card.setLayout(layout)
        greeting_layout = QVBoxLayout()
        welcome_text = QLabel(f"Good {self.get_greeting()}, Inspector!")
        welcome_text.setStyleSheet("color: white; font-size: 24px; font-weight: 700;")
        greeting_layout.addWidget(welcome_text)
        date_text = QLabel(QDateTime.currentDateTime().toString("dddd, MMMM d, yyyy"))
        date_text.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 13px;")
        greeting_layout.addWidget(date_text)
        layout.addLayout(greeting_layout)
        layout.addStretch()
        stats_layout = QVBoxLayout()
        stats_layout.setAlignment(Qt.AlignRight)
        today_stats = QLabel("Today's Progress")
        today_stats.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px;")
        stats_layout.addWidget(today_stats)
        self.today_progress = QProgressBar()
        self.today_progress.setStyleSheet("""
            QProgressBar { border: none; background: rgba(255,255,255,0.2); border-radius: 10px; height: 6px; }
            QProgressBar::chunk { background: white; border-radius: 10px; }
        """)
        self.today_progress.setFixedWidth(200)
        stats_layout.addWidget(self.today_progress)
        self.today_count = QLabel("0 / 100 inspections")
        self.today_count.setStyleSheet("color: white; font-size: 12px; font-weight: 500;")
        stats_layout.addWidget(self.today_count)
        layout.addLayout(stats_layout)
        return card

    def create_quick_actions(self):
        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 16px; border: 1px solid #E5E8EC;")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 15))
        card.setGraphicsEffect(shadow)
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        card.setLayout(layout)
        title = QLabel("Quick Actions")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1F2937;")
        layout.addWidget(title)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        actions = [
            ("📝", "New Inspection", "#4A90E2"),
            ("📊", "Export Report", "#50C878"),
            ("🔍", "View Analytics", "#FFB347"),
            ("⚙️", "Settings", "#6B7280")
        ]
        self.action_buttons = []
        for icon, text, color in actions:
            btn = ModernButton(text, color, icon)
            btn.setMinimumHeight(45)
            buttons_layout.addWidget(btn)
            self.action_buttons.append(btn)
        layout.addLayout(buttons_layout)
        return card

    # ---------- Helpers ----------
    def update_time(self):
        self.time_label.setText(QDateTime.currentDateTime().toString("hh:mm:ss A"))

    def get_greeting(self):
        hour = QDateTime.currentDateTime().time().hour()
        if hour < 12:
            return "Morning"
        elif hour < 17:
            return "Afternoon"
        else:
            return "Evening"

    @staticmethod
    def _extract_model_from_remarks(remarks):
        """Fallback: parse model from remarks if not in column"""
        if not remarks:
            return None
        match = re.search(r'Model:\s*([^|\n]+)', remarks)
        if match:
            return match.group(1).strip()
        return None

        # ---------- Core Data Fetching ----------
    def get_fault_repair_data(self, date_str: str = None):
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        try:
            # Semi faults – exact 'Semi Test'
            semi_data = self.db.execute_query("""
                SELECT 
                    COALESCE(line, 'Unknown') as line,
                    COALESCE(model, 'Unknown') as model,
                    remarks,
                    SUM(COALESCE(rejected_quantity, 0)) as total_faults
                FROM inspections
                WHERE inspection_type = 'Semi Test'
                AND CAST(inspection_date AS DATE) = ?
                GROUP BY line, model, remarks
            """, (date_str,), fetch_all=True) or []

            # MMI faults – exact 'MMI Test'
            mmi_data = self.db.execute_query("""
                SELECT 
                    COALESCE(line, 'Unknown') as line,
                    COALESCE(model, 'Unknown') as model,
                    remarks,
                    SUM(COALESCE(rejected_quantity, 0)) as total_faults
                FROM inspections
                WHERE inspection_type = 'MMI Test'
                AND CAST(inspection_date AS DATE) = ?
                GROUP BY line, model, remarks
            """, (date_str,), fetch_all=True) or []

            # Repairs (unchanged)
            repairs_data = self.db.execute_query("""
                SELECT 
                    COALESCE(line, 'Unknown') as line,
                    COALESCE(model, 'Unknown') as model,
                    SUM(COALESCE(total_qty, 0)) as repairs
                FROM rework_root_cause
                WHERE record_date = ?
                GROUP BY line, model
            """, (date_str,), fetch_all=True) or []

            print(f"[Debug] semi rows: {len(semi_data)}, mmi rows: {len(mmi_data)}, repair rows: {len(repairs_data)} for {date_str}")

            # --- (rest of the method remains exactly the same – combining logic) ---
            combined = {}

            # Process semi
            for row in semi_data:
                model = row['model']
                if model == 'Unknown' and row.get('remarks'):
                    parsed = self._extract_model_from_remarks(row['remarks'])
                    if parsed:
                        model = parsed
                key = (model, row['line'])
                combined[key] = {
                    'model': model,
                    'line': row['line'],
                    'semi_faults': row['total_faults'],
                    'mmi_faults': 0,
                    'repairs': 0
                }

            # Process mmi
            for row in mmi_data:
                model = row['model']
                if model == 'Unknown' and row.get('remarks'):
                    parsed = self._extract_model_from_remarks(row['remarks'])
                    if parsed:
                        model = parsed
                key = (model, row['line'])
                if key in combined:
                    combined[key]['mmi_faults'] = row['total_faults']
                else:
                    combined[key] = {
                        'model': model,
                        'line': row['line'],
                        'semi_faults': 0,
                        'mmi_faults': row['total_faults'],
                        'repairs': 0
                    }

            # Process repairs
            for row in repairs_data:
                key = (row['model'], row['line'])
                if key in combined:
                    combined[key]['repairs'] = row['repairs']
                else:
                    combined[key] = {
                        'model': row['model'],
                        'line': row['line'],
                        'semi_faults': 0,
                        'mmi_faults': 0,
                        'repairs': row['repairs']
                    }

            # Build final result
            result = []
            for (model, line), vals in combined.items():
                total_faults = vals['semi_faults'] + vals['mmi_faults']
                unresolved = total_faults - vals['repairs']
                result.append({
                    'model': vals['model'],
                    'line': vals['line'],
                    'semi_faults': vals['semi_faults'],
                    'mmi_faults': vals['mmi_faults'],
                    'total_faults': total_faults,
                    'repairs': vals['repairs'],
                    'unresolved': unresolved
                })

            if result:
                print(f"✅ Loaded {len(result)} entries for {date_str}")
                return result
            else:
                print(f"⚠️ No data for {date_str}")
                return []

        except Exception as e:
            print(f"❌ Error in get_fault_repair_data: {e}")
            import traceback
            traceback.print_exc()
            return []

 
    def _get_latest_date_with_data(self):
        """Returns the latest date that has either inspections or rework records."""
        query = """
            SELECT MAX(latest_date) as latest_date FROM (
                SELECT MAX(CAST(inspection_date AS DATE)) as latest_date FROM inspections
                UNION
                SELECT MAX(record_date) as latest_date FROM rework_root_cause
            ) as dates
        """
        row = self.db.execute_query(query, fetch_one=True)
        if row and row['latest_date']:
            return row['latest_date']
        return None

    # ---------- UI Update Methods ----------
    def update_line_cards(self, data):
        # Clear existing cards
        for i in reversed(range(self.line_cards_layout.count())):
            widget = self.line_cards_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Filter by selected model
        filtered_data = data
        if self.current_model_filter != "All Models":
            filtered_data = [row for row in data if row['model'] == self.current_model_filter]

        # Aggregate by line
        line_agg = {}
        for row in filtered_data:
            line = row['line']
            if line not in line_agg:
                line_agg[line] = {"semi": 0, "mmi": 0, "repairs": 0, "unresolved": 0}
            line_agg[line]["semi"] += row.get('semi_faults', 0)
            line_agg[line]["mmi"] += row.get('mmi_faults', 0)
            line_agg[line]["repairs"] += row.get('repairs', 0)
            line_agg[line]["unresolved"] += row.get('unresolved', 0)

        row_idx = 0
        col_idx = 0
        for line, vals in line_agg.items():
            total_faults = vals["semi"] + vals["mmi"]
            unresolved = vals["unresolved"]
            repair_rate = (vals["repairs"] / total_faults * 100) if total_faults > 0 else 0

            card = QFrame()
            card.setStyleSheet("background: white; border-radius: 16px; border: 1px solid #E5E8EC; padding: 15px;")
            layout = QVBoxLayout(card)
            layout.setSpacing(8)

            title = QLabel(f"Line {line}")
            title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1F2937;")
            layout.addWidget(title)

            semi = QLabel(f"🔧 Semi: {vals['semi']}")
            semi.setStyleSheet("color: #FF6B6B; font-size: 13px;")
            layout.addWidget(semi)

            mmi = QLabel(f"📟 MMI: {vals['mmi']}")
            mmi.setStyleSheet("color: #FFB347; font-size: 13px;")
            layout.addWidget(mmi)

            repairs = QLabel(f"✅ Repairs: {vals['repairs']}")
            repairs.setStyleSheet("color: #50C878; font-size: 13px; font-weight: 600;")
            layout.addWidget(repairs)

            unresolved_label = QLabel()
            if unresolved < 0:
                unresolved_label.setText(f"⚠️ Over-repair: {-unresolved}")
                unresolved_label.setStyleSheet("color: #DC2626; font-size: 13px; font-weight: bold;")
            elif unresolved > 0:
                unresolved_label.setText(f"⏳ Pending: {unresolved}")
                unresolved_label.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: bold;")
            else:
                unresolved_label.setText("✅ No pending")
                unresolved_label.setStyleSheet("color: #10B981; font-size: 13px;")
            layout.addWidget(unresolved_label)

            rate_bar = QProgressBar()
            rate_bar.setRange(0, 100)
            rate_bar.setValue(int(repair_rate))
            rate_bar.setFormat(f"Repair Rate: {repair_rate:.1f}%")
            rate_bar.setStyleSheet("""
                QProgressBar { border: none; background: #E5E8EC; border-radius: 8px; height: 20px; text-align: center; }
                QProgressBar::chunk { background: #50C878; border-radius: 8px; }
            """)
            layout.addWidget(rate_bar)

            self.line_cards_layout.addWidget(card, row_idx, col_idx)
            col_idx += 1
            if col_idx >= 3:
                col_idx = 0
                row_idx += 1

    def update_model_table(self, data):
        self.model_table.setRowCount(len(data))
        for row, d in enumerate(data):
            model = d.get('model', 'N/A')
            line = d.get('line', 'N/A')
            semi = d.get('semi_faults', 0)
            mmi = d.get('mmi_faults', 0)
            repairs = d.get('repairs', 0)
            unresolved = d.get('unresolved', 0)
            total_faults = semi + mmi

            self.model_table.setItem(row, 0, QTableWidgetItem(model))
            self.model_table.setItem(row, 1, QTableWidgetItem(line))
            self.model_table.setItem(row, 2, QTableWidgetItem(str(semi)))
            self.model_table.setItem(row, 3, QTableWidgetItem(str(mmi)))
            self.model_table.setItem(row, 4, QTableWidgetItem(str(total_faults)))
            self.model_table.setItem(row, 5, QTableWidgetItem(str(repairs)))

            unresolved_item = QTableWidgetItem()
            if unresolved < 0:
                unresolved_item.setText(f"-{-unresolved} (over)")
                unresolved_item.setForeground(QColor("#DC2626"))
            elif unresolved > 0:
                unresolved_item.setText(str(unresolved))
                unresolved_item.setForeground(QColor("#F59E0B"))
            else:
                unresolved_item.setText("0")
                unresolved_item.setForeground(QColor("#10B981"))
            self.model_table.setItem(row, 6, unresolved_item)

        self.model_table.resizeRowsToContents()
        self.model_table.updateGeometry()

    def on_model_filter_changed(self, model):
        self.current_model_filter = model
        if hasattr(self, 'full_data'):
            self.update_line_cards(self.full_data)

    # ---------- Main Refresh ----------
    def refresh_data(self):
        try:
            # Update today's progress
            stats = self.db.get_inspection_statistics() or {}
            today_count = stats.get('today_inspections', 0) or 0
            self.today_count.setText(f"{today_count} / 100 inspections")
            self.today_progress.setValue(min(int(today_count), 100))

            # Try today's date first
            today_str = datetime.now().strftime('%Y-%m-%d')
            data = self.get_fault_repair_data(today_str)

            # If no data for today, fallback to latest date with any record
            if not data:
                latest_date = self._get_latest_date_with_data()
                if latest_date:
                    date_str = latest_date.strftime('%Y-%m-%d')
                    print(f"⚠️ No data for today, falling back to latest date: {date_str}")
                    data = self.get_fault_repair_data(date_str)
                else:
                    print("❌ No data at all in database – using dummy")
                    data = self._get_dummy_data()

            self.full_data = data
            self.update_line_cards(data)
            self.update_model_table(data)

            # Populate model combo
            models = sorted(set(row['model'] for row in data if row['model'] != "Unknown"))
            if not models and data:
                models = ["Unknown"]
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            self.model_combo.addItem("All Models")
            for m in models:
                self.model_combo.addItem(m)
            idx = self.model_combo.findText(self.current_model_filter)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                self.current_model_filter = "All Models"
                self.model_combo.setCurrentIndex(0)
            self.model_combo.blockSignals(False)

            self.updateGeometry()

        except Exception as e:
            print(f"❌ Error refreshing dashboard: {e}")
            import traceback
            traceback.print_exc()
    def _get_dummy_data(self):
        """Fallback dummy data – only used when database is completely empty."""
        return [
            {"model": "NEW 16 PRO", "line": "202", "semi_faults": 0, "mmi_faults": 0,
             "repairs": 0, "unresolved": 0, "total_faults": 0},
        ]