import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QLineEdit, QPushButton, QScrollArea,
    QGroupBox, QComboBox, QTextEdit, QDateEdit, QTabWidget, 
    QSpinBox, QApplication, QDialog, QListWidget, QListWidgetItem, 
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox
)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QPalette, QLinearGradient, QBrush
from database import Database
from custom_dialogs import CustomMessageBox   # <-- modern message box

# Remove the local CustomMessageBox class definition entirely


class FaultManagementWidget(QWidget):
    """Admin panel to manage faults dynamically"""
    
    def __init__(self, db: Database, user_data):
        super().__init__()
        self.db = db
        self.user = user_data
        self.current_category_id = None
        self.current_category_name = None
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Small Compact Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 10px;
            }
        """)
        header.setFixedHeight(50)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        header_title = QLabel("🔧 Fault Management")
        header_title.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: white;
            font-family: 'Segoe UI';
        """)
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        
        # Stats label
        self.stats_label = QLabel("Ready")
        self.stats_label.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 11px;")
        header_layout.addWidget(self.stats_label)
        
        header.setLayout(header_layout)
        main_layout.addWidget(header)
        
        # Main content area
        content_widget = QWidget()
        content_widget.setStyleSheet("background: #f0f2f5; border-radius: 10px;")
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        # Left Panel - Categories (30% width)
        left_panel = self.create_left_panel()
        content_layout.addWidget(left_panel)
        
        # Right Panel - Faults Management (70% width)
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel)
        
        content_layout.setStretchFactor(left_panel, 30)
        content_layout.setStretchFactor(right_panel, 70)
        
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)
        
        self.setLayout(main_layout)
        self.setStyleSheet("background: #f0f2f5;")
    
    def create_left_panel(self):
        """Create left panel with station and category selection"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Station Selection - Compact
        station_title = QLabel("📡 Station")
        station_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #2d3748;")
        layout.addWidget(station_title)
        
        self.station_combo = QComboBox()
        self.station_combo.addItems(["Semi Test", "MMI Test", "Appearance Test", "Final Test"])
        self.station_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 12px;
                background: white;
            }
            QComboBox:focus {
                border-color: #667eea;
            }
        """)
        self.station_combo.currentTextChanged.connect(self.on_station_changed)
        layout.addWidget(self.station_combo)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background: #e2e8f0; max-height: 1px; margin: 8px 0;")
        layout.addWidget(divider)
        
        # Categories Section
        categories_title = QLabel("📂 Categories")
        categories_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #2d3748;")
        layout.addWidget(categories_title)
        
        # Search box - Compact
        self.category_search = QLineEdit()
        self.category_search.setPlaceholderText("🔍 Search...")
        self.category_search.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        self.category_search.textChanged.connect(self.filter_categories)
        layout.addWidget(self.category_search)
        
        self.categories_list = QListWidget()
        self.categories_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 3px;
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 1px;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
            }
        """)
        self.categories_list.itemClicked.connect(self.on_category_selected)
        layout.addWidget(self.categories_list)
        
        # Add Category Button - Compact
        add_category_btn = QPushButton("➕ New Category")
        add_category_btn.setStyleSheet("""
            QPushButton {
                background: #48bb78;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #38a169;
            }
        """)
        add_category_btn.clicked.connect(self.add_new_category)
        layout.addWidget(add_category_btn)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def create_right_panel(self):
        """Create right panel with faults management - BIG TABLE"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Category Header - Compact
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 8px;
            }
        """)
        header_frame.setFixedHeight(45)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        self.category_icon = QLabel("📁")
        self.category_icon.setStyleSheet("font-size: 20px; background: transparent;")
        header_layout.addWidget(self.category_icon)
        
        self.category_header = QLabel("Select Category")
        self.category_header.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            color: white;
            background: transparent;
        """)
        header_layout.addWidget(self.category_header)
        header_layout.addStretch()
        
        self.fault_count_label = QLabel("")
        self.fault_count_label.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 11px; background: transparent;")
        header_layout.addWidget(self.fault_count_label)
        
        header_frame.setLayout(header_layout)
        layout.addWidget(header_frame)
        
        # Add New Fault Section - Compact
        add_fault_group = QGroupBox("➕ Add Fault")
        add_fault_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #2d3748;
            }
        """)
        add_fault_layout = QHBoxLayout()
        add_fault_layout.setSpacing(10)
        
        self.fault_name_input = QLineEdit()
        self.fault_name_input.setPlaceholderText("🔧 Fault name...")
        self.fault_name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        add_fault_layout.addWidget(self.fault_name_input)
        
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["🔴 Critical", "🟠 Major", "🟡 Minor"])
        self.severity_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 12px;
                min-width: 100px;
            }
        """)
        add_fault_layout.addWidget(self.severity_combo)
        
        add_btn = QPushButton("➕ Add")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #667eea;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5a67d8;
            }
        """)
        add_btn.clicked.connect(self.add_new_fault)
        add_fault_layout.addWidget(add_btn)
        
        add_fault_group.setLayout(add_fault_layout)
        layout.addWidget(add_fault_group)
        
        # Faults Table - BIG SIZE
        faults_title = QLabel("📋 Existing Faults")
        faults_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #2d3748; margin-top: 5px;")
        layout.addWidget(faults_title)
        
        # Create BIG Table for faults
        self.faults_table = QTableWidget()
        self.faults_table.setColumnCount(3)
        self.faults_table.setHorizontalHeaderLabels(["Severity", "Fault Name", "Fault Code"])
        self.faults_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                font-size: 13px;
                gridline-color: #e2e8f0;
                outline: none;
            }
            QTableWidget::item {
                padding: 12px;
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
            }
            QHeaderView::section {
                background: #f7fafc;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self.faults_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.faults_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.faults_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.faults_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.faults_table.setSelectionMode(QTableWidget.SingleSelection)
        self.faults_table.verticalHeader().setVisible(False)
        self.faults_table.setAlternatingRowColors(True)
        self.faults_table.setMinimumHeight(400)  # BIG TABLE
        layout.addWidget(self.faults_table)
        
        # Action Buttons - Compact
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        edit_btn = QPushButton("✏️ Edit")
        edit_btn.setStyleSheet("""
            QPushButton {
                background: #ed8936;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #dd6b20;
            }
        """)
        edit_btn.clicked.connect(self.edit_selected_fault)
        button_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background: #e53e3e;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c53030;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_fault)
        button_layout.addWidget(delete_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #4a5568;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2d3748;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        panel.setLayout(layout)
        return panel
    
    def filter_categories(self):
        """Filter categories based on search text"""
        search_text = self.category_search.text().lower()
        for i in range(self.categories_list.count()):
            item = self.categories_list.item(i)
            item.setHidden(search_text not in item.text().lower())
    
    def load_data(self):
        """Load all data from database"""
        self.current_category_id = None
        self.current_category_name = None
        self.load_categories()
    
    def load_categories(self):
        """Load categories for selected station"""
        station = self.station_combo.currentText()
        categories = self.db.get_fault_categories(station)
        
        self.categories_list.clear()
        
        if categories:
            for category in categories:
                category_name = category.get('category_name', '')
                item = QListWidgetItem(f"{category_name}")
                item.setData(Qt.UserRole, category.get('id'))
                self.categories_list.addItem(item)
            
            self.stats_label.setText(f"📊 {len(categories)} Cats")
    
    def on_station_changed(self, station):
        """When station changes, reload categories"""
        self.load_categories()
        self.category_header.setText("Select Category")
        self.fault_count_label.setText("")
        self.faults_table.setRowCount(0)
        self.current_category_id = None
        self.category_search.clear()
    
    def on_category_selected(self, item):
        """When category is selected, load faults"""
        self.current_category_id = item.data(Qt.UserRole)
        self.current_category_name = item.text()
        
        self.category_header.setText(f"{self.current_category_name}")
        self.load_faults()
    
    def load_faults(self):
        """Load faults for selected category"""
        if not self.current_category_id:
            return
        
        faults = self.db.get_faults_by_category(self.current_category_id)
        self.faults_table.setRowCount(0)
        
        if faults:
            self.faults_table.setRowCount(len(faults))
            self.fault_count_label.setText(f"🔧 {len(faults)} Faults")
            
            for row, fault in enumerate(faults):
                fault_name = fault.get('fault_name', '')
                severity = fault.get('severity', 'Minor')
                fault_code = fault.get('fault_code', '')
                
                severity_icon = {
                    'Critical': '🔴 Critical',
                    'Major': '🟠 Major',
                    'Minor': '🟡 Minor'
                }.get(severity, '⚪ Minor')
                
                severity_item = QTableWidgetItem(severity_icon)
                severity_item.setData(Qt.UserRole, fault.get('id'))
                
                if severity == 'Critical':
                    severity_item.setForeground(QColor("#e53e3e"))
                elif severity == 'Major':
                    severity_item.setForeground(QColor("#ed8936"))
                else:
                    severity_item.setForeground(QColor("#d69e2e"))
                
                self.faults_table.setItem(row, 0, severity_item)
                
                name_item = QTableWidgetItem(fault_name)
                name_item.setData(Qt.UserRole, fault.get('id'))
                self.faults_table.setItem(row, 1, name_item)
                
                code_item = QTableWidgetItem(fault_code if fault_code else "-")
                code_item.setData(Qt.UserRole, fault.get('id'))
                self.faults_table.setItem(row, 2, code_item)
            
            self.faults_table.resizeRowsToContents()
        else:
            self.fault_count_label.setText("🔧 No Faults")
    
    def get_selected_fault_id(self):
        """Get selected fault ID from table"""
        current_row = self.faults_table.currentRow()
        if current_row >= 0:
            item = self.faults_table.item(current_row, 0)
            if item:
                return item.data(Qt.UserRole)
        return None
    
    def add_new_fault(self):
        """Add new fault to current category"""
        if not self.current_category_id:
            CustomMessageBox.show_warning(self, "No Category", "Please select a category first!")
            return
        
        fault_name = self.fault_name_input.text().strip()
        if not fault_name:
            CustomMessageBox.show_warning(self, "Validation Error", "Please enter fault name!")
            return
        
        severity_text = self.severity_combo.currentText()
        severity = severity_text.split(' ')[-1] if ' ' in severity_text else severity_text
        
        try:
            fault_id = self.db.add_fault(
                self.current_category_id,
                fault_name,
                severity=severity,
                created_by=self.user.get('id')
            )
            
            if fault_id:
                CustomMessageBox.show_success(self, "Success", f"✅ Fault '{fault_name}' added!")
                self.fault_name_input.clear()
                self.load_faults()
                
                faults = self.db.get_faults_by_category(self.current_category_id)
                self.fault_count_label.setText(f"🔧 {len(faults)} Faults")
            else:
                CustomMessageBox.show_error(self, "Error", "Failed to add fault!")
                
        except Exception as e:
            CustomMessageBox.show_error(self, "Database Error", f"Error: {str(e)}")
    
    def edit_selected_fault(self):
        """Edit selected fault"""
        fault_id = self.get_selected_fault_id()
        if not fault_id:
            CustomMessageBox.show_warning(self, "No Selection", "Please select a fault to edit!")
            return
        
        current_row = self.faults_table.currentRow()
        current_name = self.faults_table.item(current_row, 1).text()
        current_severity_text = self.faults_table.item(current_row, 0).text()
        current_severity = current_severity_text.split(' ')[-1] if ' ' in current_severity_text else current_severity_text
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Fault")
        dialog.setModal(True)
        dialog.setFixedSize(400, 280)
        dialog.setStyleSheet("""
            QDialog {
                background: white;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("✏️ Edit Fault")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2d3748;")
        layout.addWidget(title_label)
        
        label1 = QLabel("Fault Name:")
        label1.setStyleSheet("font-weight: bold; color: #4a5568; font-size: 12px;")
        layout.addWidget(label1)
        
        fault_input = QLineEdit(current_name)
        fault_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 13px;
            }
        """)
        layout.addWidget(fault_input)
        
        label2 = QLabel("Severity:")
        label2.setStyleSheet("font-weight: bold; color: #4a5568; font-size: 12px; margin-top: 10px;")
        layout.addWidget(label2)
        
        severity_combo = QComboBox()
        severity_combo.addItems(["🔴 Critical", "🟠 Major", "🟡 Minor"])
        for i in range(severity_combo.count()):
            if current_severity in severity_combo.itemText(i):
                severity_combo.setCurrentIndex(i)
                break
        severity_combo.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 13px;
            }
        """)
        layout.addWidget(severity_combo)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        save_btn = QPushButton("💾 Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #48bb78;
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #a0aec0;
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        
        def save_changes():
            new_name = fault_input.text().strip()
            new_severity_text = severity_combo.currentText()
            new_severity = new_severity_text.split(' ')[-1] if ' ' in new_severity_text else new_severity_text
            
            if new_name:
                self.db.update_fault(fault_id, fault_name=new_name, severity=new_severity, updated_by=self.user.get('id'))
                CustomMessageBox.show_success(self, "Success", f"✅ Fault updated!")
                dialog.accept()
                self.load_faults()
        
        save_btn.clicked.connect(save_changes)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def delete_selected_fault(self):
        """Delete selected fault"""
        fault_id = self.get_selected_fault_id()
        if not fault_id:
            CustomMessageBox.show_warning(self, "No Selection", "Please select a fault to delete!")
            return
        
        current_row = self.faults_table.currentRow()
        fault_name = self.faults_table.item(current_row, 1).text()
        
        reply = CustomMessageBox.show_question(self, "Confirm Delete", 
            f"Delete '{fault_name}'?\nThis cannot be undone!")
        
        if reply == QDialog.Accepted:
            self.db.delete_fault(fault_id, soft_delete=True, deleted_by=self.user.get('id'))
            CustomMessageBox.show_success(self, "Success", "✅ Fault deleted!")
            self.load_faults()
    
    def add_new_category(self):
        """Add new category"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Category")
        dialog.setModal(True)
        dialog.setFixedSize(450, 380)
        dialog.setStyleSheet("""
            QDialog {
                background: white;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("➕ Add Category")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2d3748;")
        layout.addWidget(title_label)
        
        label1 = QLabel("Category Name:")
        label1.setStyleSheet("font-weight: bold; color: #4a5568; font-size: 12px;")
        layout.addWidget(label1)
        
        category_input = QLineEdit()
        category_input.setPlaceholderText("e.g., BATTERY, NETWORK...")
        category_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 13px;
            }
        """)
        layout.addWidget(category_input)
        
        label2 = QLabel("Station Type:")
        label2.setStyleSheet("font-weight: bold; color: #4a5568; font-size: 12px; margin-top: 10px;")
        layout.addWidget(label2)
        
        station_combo = QComboBox()
        station_combo.addItems(["Semi Test", "MMI Test", "Appearance Test", "Final Test"])
        station_combo.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 13px;
            }
        """)
        layout.addWidget(station_combo)
        
        label3 = QLabel("Icon (optional):")
        label3.setStyleSheet("font-weight: bold; color: #4a5568; font-size: 12px; margin-top: 10px;")
        layout.addWidget(label3)
        
        icon_input = QLineEdit()
        icon_input.setPlaceholderText("e.g., 🔋, 📡, 🌐")
        icon_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 13px;
            }
        """)
        layout.addWidget(icon_input)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        save_btn = QPushButton("💾 Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #48bb78;
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #a0aec0;
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        
        def save_category():
            category_name = category_input.text().strip()
            station_type = station_combo.currentText()
            icon = icon_input.text().strip()
            
            if category_name:
                self.db.add_fault_category(category_name, station_type, icon=icon, created_by=self.user.get('id'))
                CustomMessageBox.show_success(self, "Success", f"✅ Category added!")
                dialog.accept()
                self.load_categories()
            else:
                CustomMessageBox.show_warning(self, "Error", "Enter category name!")
        
        save_btn.clicked.connect(save_category)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def refresh_data(self):
        """Refresh all data"""
        self.load_categories()
        if self.current_category_id:
            self.load_faults()
        CustomMessageBox.show_success(self, "Refreshed", "✅ Data refreshed!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    db = Database()
    user = {'id': 1, 'full_name': 'Admin', 'role': 'admin'}
    
    widget = FaultManagementWidget(db, user)
    widget.setWindowTitle("Fault Management System")
    widget.setGeometry(100, 100, 1200, 700)
    widget.show()
    
    sys.exit(app.exec_())