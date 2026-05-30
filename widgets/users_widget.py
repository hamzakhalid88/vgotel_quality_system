from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QMessageBox,
                             QDialog, QFormLayout, QLineEdit, QComboBox,
                             QCheckBox, QDialogButtonBox, QLabel, QFrame,
                             QGridLayout, QGroupBox, QHeaderView, QMenu)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
from database import Database
from config import ROLES
import re


class UserDialog(QDialog):
    """Enhanced User Dialog with validation"""
    
    user_saved = pyqtSignal(dict)
    
    def __init__(self, db: Database, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.setup_ui()
        
        if user_data:
            self.load_user_data()
            self.setWindowTitle("✏️ Edit User")
        else:
            self.setWindowTitle("➕ Add New User")
    
    def setup_ui(self):
        self.setModal(True)
        self.setFixedSize(500, 600)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)
        self.setLayout(main_layout)
        
        # Header
        header = QLabel("👤 User Information")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e3c72;")
        main_layout.addWidget(header)
        
        # Form Group
        form_group = QGroupBox("User Details")
        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(15)
        form_layout.setHorizontalSpacing(20)
        form_group.setLayout(form_layout)
        
        # Username
        username_label = QLabel("Username *")
        username_label.setStyleSheet("font-weight: bold; color: #555;")
        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter username")
        if self.user_data:
            self.username.setReadOnly(True)
        form_layout.addWidget(username_label, 0, 0)
        form_layout.addWidget(self.username, 0, 1)
        
        # Full Name
        full_name_label = QLabel("Full Name *")
        full_name_label.setStyleSheet("font-weight: bold; color: #555;")
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Enter full name")
        form_layout.addWidget(full_name_label, 1, 0)
        form_layout.addWidget(self.full_name, 1, 1)
        
        # Email
        email_label = QLabel("Email")
        email_label.setStyleSheet("font-weight: bold; color: #555;")
        self.email = QLineEdit()
        self.email.setPlaceholderText("user@example.com")
        form_layout.addWidget(email_label, 2, 0)
        form_layout.addWidget(self.email, 2, 1)
        
        # Phone
        phone_label = QLabel("Phone")
        phone_label.setStyleSheet("font-weight: bold; color: #555;")
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+92XXXXXXXXXX")
        form_layout.addWidget(phone_label, 3, 0)
        form_layout.addWidget(self.phone, 3, 1)
        
        # Role
        role_label = QLabel("Role *")
        role_label.setStyleSheet("font-weight: bold; color: #555;")
        self.role = QComboBox()
        for role in ROLES.keys():
            self.role.addItem(role.title(), role)
        form_layout.addWidget(role_label, 4, 0)
        form_layout.addWidget(self.role, 4, 1)
        
        # Department
        dept_label = QLabel("Department")
        dept_label.setStyleSheet("font-weight: bold; color: #555;")
        self.department = QComboBox()
        self.department.addItems(["Quality Control", "Quality Assurance", "Production", 
                                  "Maintenance", "R&D", "Management", "IT"])
        form_layout.addWidget(dept_label, 5, 0)
        form_layout.addWidget(self.department, 5, 1)
        
        main_layout.addWidget(form_group)
        
        # Password Section
        password_group = QGroupBox("Password Settings")
        password_layout = QGridLayout()
        password_group.setLayout(password_layout)
        
        password_label = QLabel("Password")
        password_label.setStyleSheet("font-weight: bold; color: #555;")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Enter password" if not self.user_data else "Leave blank to keep current")
        password_layout.addWidget(password_label, 0, 0)
        password_layout.addWidget(self.password, 0, 1)
        
        confirm_label = QLabel("Confirm Password")
        confirm_label.setStyleSheet("font-weight: bold; color: #555;")
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.confirm_password.setPlaceholderText("Confirm password")
        password_layout.addWidget(confirm_label, 1, 0)
        password_layout.addWidget(self.confirm_password, 1, 1)
        
        # Status
        status_label = QLabel("Status")
        status_label.setStyleSheet("font-weight: bold; color: #555;")
        self.is_active = QCheckBox("Active")
        self.is_active.setChecked(True)
        password_layout.addWidget(status_label, 2, 0)
        password_layout.addWidget(self.is_active, 2, 1)
        
        main_layout.addWidget(password_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.save_btn = QPushButton("💾 Save User")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.validate_and_accept)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        # Apply styles
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit, QComboBox {
                padding: 8px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #1e3c72;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:first {
                background-color: #1e3c72;
                color: white;
                border: none;
            }
            QPushButton:first:hover {
                background-color: #2a5298;
            }
            QPushButton:last {
                background-color: #dc3545;
                color: white;
                border: none;
            }
            QPushButton:last:hover {
                background-color: #c82333;
            }
        """)
    
    def load_user_data(self):
        """Load user data into form - ALL converted to string"""
        self.username.setText(str(self.user_data.get('username', '')))
        self.full_name.setText(str(self.user_data.get('full_name', '')))
        self.email.setText(str(self.user_data.get('email', '')))
        self.phone.setText(str(self.user_data.get('phone', '')))
        
        role = self.user_data.get('role', 'viewer')
        index = self.role.findData(role)
        if index >= 0:
            self.role.setCurrentIndex(index)
        
        dept = self.user_data.get('department', 'Quality Control')
        dept_index = self.department.findText(str(dept))
        if dept_index >= 0:
            self.department.setCurrentIndex(dept_index)
        
        self.is_active.setChecked(bool(self.user_data.get('is_active', True)))
    
    def validate_and_accept(self):
        """Validate form data"""
        if not self.user_data:
            if not self.username.text().strip():
                QMessageBox.warning(self, "Error", "❌ Username is required!")
                return
            
            if len(self.username.text().strip()) < 3:
                QMessageBox.warning(self, "Error", "❌ Username must be at least 3 characters!")
                return
        
        if not self.full_name.text().strip():
            QMessageBox.warning(self, "Error", "❌ Full name is required!")
            return
        
        if not self.user_data:
            if not self.password.text():
                QMessageBox.warning(self, "Error", "❌ Password is required!")
                return
            
            if len(self.password.text()) < 6:
                QMessageBox.warning(self, "Error", "❌ Password must be at least 6 characters!")
                return
            
            if self.password.text() != self.confirm_password.text():
                QMessageBox.warning(self, "Error", "❌ Passwords do not match!")
                return
        else:
            if self.password.text():
                if len(self.password.text()) < 6:
                    QMessageBox.warning(self, "Error", "❌ Password must be at least 6 characters!")
                    return
                
                if self.password.text() != self.confirm_password.text():
                    QMessageBox.warning(self, "Error", "❌ Passwords do not match!")
                    return
        
        self.accept()
    
    def get_user_data(self):
        """Get user data from form"""
        data = {
            'full_name': self.full_name.text().strip(),
            'email': self.email.text().strip(),
            'phone': self.phone.text().strip(),
            'role': self.role.currentData(),
            'department': self.department.currentText(),
            'is_active': self.is_active.isChecked()
        }
        
        if not self.user_data:
            data['username'] = self.username.text().strip()
            data['password'] = self.password.text()
        elif self.password.text():
            data['password'] = self.password.text()
        
        return data


class UsersWidget(QWidget):
    """Users Management Widget"""
    
    def __init__(self, db: Database, user_role: str):
        super().__init__()
        self.db = db
        self.user_role = user_role
        self.all_users = []
        self.setup_ui()
        self.load_users()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e3c72, stop:1 #2a5298);
                border-radius: 12px;
            }
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(20, 15, 20, 15)
        header_frame.setLayout(header_layout)
        
        title = QLabel("👥 User Management")
        title.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #B3D4FC; font-size: 12px;")
        header_layout.addWidget(self.stats_label)
        
        layout.addWidget(header_frame)
        
        # Search Bar
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(15, 10, 15, 10)
        search_frame.setLayout(search_layout)
        
        search_label = QLabel("🔍")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search users...")
        self.search_input.textChanged.connect(self.filter_users)
        search_layout.addWidget(self.search_input)
        
        layout.addWidget(search_frame)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add User")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_user)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_users)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Users Table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels([
            "Username", "Full Name", "Email", "Role", "Status", "Last Login"
        ])
        
        self.users_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
            QHeaderView::section {
                background-color: #1e3c72;
                color: white;
                padding: 10px;
                font-weight: bold;
            }
        """)
        
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.users_table)
        
        # Apply button styles
        self.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:first {
                background-color: #28a745;
                color: white;
                border: none;
            }
            QPushButton:first:hover {
                background-color: #218838;
            }
            QPushButton:last {
                background-color: #17a2b8;
                color: white;
                border: none;
            }
            QPushButton:last:hover {
                background-color: #138496;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
            }
        """)
    
    def load_users(self):
        """Load users into table"""
        try:
            users = self.db.get_all_users()
            self.all_users = users
            self.display_users(users)
            
            active_count = sum(1 for u in users if u.get('is_active'))
            self.stats_label.setText(f"Total: {len(users)} | Active: {active_count}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load users: {str(e)}")
    
    def display_users(self, users):
        """Display users in table - ALL converted to string"""
        self.users_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            # Username
            self.users_table.setItem(row, 0, QTableWidgetItem(str(user.get('username', ''))))
            
            # Full Name
            self.users_table.setItem(row, 1, QTableWidgetItem(str(user.get('full_name', ''))))
            
            # Email
            self.users_table.setItem(row, 2, QTableWidgetItem(str(user.get('email', ''))))
            
            # Role
            role = str(user.get('role', 'viewer'))
            role_item = QTableWidgetItem(role.upper())
            if role == 'admin':
                role_item.setForeground(QBrush(QColor(0xdc, 0x35, 0x45)))
            elif role == 'manager':
                role_item.setForeground(QBrush(QColor(0xff, 0x98, 0x00)))
            elif role == 'inspector':
                role_item.setForeground(QBrush(QColor(0x28, 0xa7, 0x45)))
            self.users_table.setItem(row, 3, role_item)
            
            # Status
            is_active = user.get('is_active', False)
            status_text = "🟢 Active" if is_active else "🔴 Inactive"
            status_item = QTableWidgetItem(status_text)
            if is_active:
                status_item.setForeground(QBrush(QColor(0x28, 0xa7, 0x45)))
            else:
                status_item.setForeground(QBrush(QColor(0xdc, 0x35, 0x45)))
            self.users_table.setItem(row, 4, status_item)
            
            # Last Login - Convert to string
            last_login = user.get('last_login')
            if last_login:
                last_login_str = str(last_login)[:19]
            else:
                last_login_str = 'Never'
            self.users_table.setItem(row, 5, QTableWidgetItem(last_login_str))
        
        self.users_table.resizeColumnsToContents()
    
    def filter_users(self):
        """Filter users based on search"""
        search_text = self.search_input.text().lower()
        
        if not search_text:
            self.display_users(self.all_users)
            return
        
        filtered = []
        for user in self.all_users:
            if (search_text in str(user.get('username', '')).lower() or
                search_text in str(user.get('full_name', '')).lower() or
                search_text in str(user.get('email', '')).lower() or
                search_text in str(user.get('role', '')).lower()):
                filtered.append(user)
        
        self.display_users(filtered)
    
    def add_user(self):
        """Add new user"""
        dialog = UserDialog(self.db, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            user_data = dialog.get_user_data()
            user_id = self.db.create_user(user_data)
            if user_id:
                QMessageBox.information(self, "Success", "✅ User added successfully!")
                self.load_users()
            else:
                QMessageBox.critical(self, "Error", "❌ Failed to add user!")