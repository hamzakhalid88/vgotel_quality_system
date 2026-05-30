from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QStackedWidget, QFrame,
                             QScrollArea, QApplication)   # ← add QApplication here
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PyQt5.QtGui import QFont, QIcon
from database import Database
from config import APP_CONFIG, ROLES
from widgets.dashboard_widget import DashboardWidget
from widgets.new_entry_widget import NewEntryWidget
from widgets.reports_widget import ReportsWidget
from widgets.fault_management_widget import FaultManagementWidget
from widgets.rework_widget import ReworkWidget
from custom_dialogs import CustomMessageBox
from vgotel_loader import VgotelLoader   # Import the loader


class MainWindow(QMainWindow):
    def __init__(self, db: Database, user_data: dict):
        super().__init__()
        self.db = db
        self.user = user_data
        self.fault_widget = None

        # Show the loader before building the UI
        self.loader = VgotelLoader(duration=3000)
        self.loader.show()
        QApplication.processEvents()   # Force the loader to appear immediately

        # Build the entire UI (this may take a moment)
        self.setup_ui()

        # Close the loader and show the main window
        self.loader.finish()
        self.showMaximized()
    
    def setup_ui(self):
        self.setWindowTitle(f"{APP_CONFIG['app_name']} - Welcome {self.user['full_name']}")
        self.setStyleSheet("background-color: #1E1E1E;")
        
        # Main container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_widget.setLayout(main_layout)
        
        # ========== TOP BAR ==========
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        # ========== CONTENT AREA ==========
        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet("""
            QStackedWidget {
                background-color: #F5F5F5;
            }
        """)
        main_layout.addWidget(self.content_area, 1)
        
        # ========== ADD PAGES ==========
        permissions = ROLES.get(self.user['role'], [])
        
        # Dashboard Page (Index 0)
        self.dashboard_page = DashboardWidget(self.db)
        self.content_area.addWidget(self.dashboard_page)
        
        # New Entry Page (Index 1)
        if 'manage_inspections' in permissions:
            self.new_entry_page = NewEntryWidget(self.db, self.user)
            self.new_entry_page.data_saved.connect(self.on_data_saved)
            self.content_area.addWidget(self.new_entry_page)
        
        # Reports Page (Index 2)
        if 'view_reports' in permissions:
            self.reports_page = ReportsWidget(self.db, self.user['role'])
            self.content_area.addWidget(self.reports_page)
        
        # Fault Management Page (Index 3) – Only for admin
        if self.user['role'] == 'admin':
            self.fault_mgmt_page = FaultManagementWidget(self.db, self.user)
            self.content_area.addWidget(self.fault_mgmt_page)
        
        # Rework Station Page (Index 4) – For inspectors/managers/admin
        if 'manage_inspections' in permissions or self.user['role'] in ['admin', 'manager']:
            self.rework_page = ReworkWidget(self.db, self.user)
            self.content_area.addWidget(self.rework_page)
        
        # Set default page
        self.content_area.setCurrentIndex(0)
    
    def create_top_bar(self):
        # ... (same as before, unchanged) ...
        top_bar = QFrame()
        top_bar.setFixedHeight(70)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border-bottom: 2px solid #0D47A1;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(20)
        top_bar.setLayout(layout)
        
        # Logo Section (Left)
        logo_container = QHBoxLayout()
        logo = QLabel("🔍 QC")
        logo.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #0D47A1;
            font-family: 'Segoe UI';
        """)
        logo_container.addWidget(logo)
        company = QLabel(APP_CONFIG['company'])
        company.setStyleSheet("color: #888888; font-size: 10px; margin-left: 5px;")
        logo_container.addWidget(company)
        layout.addLayout(logo_container)
        
        layout.addStretch()
        
        # Navigation Menu (Center)
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(5)
        
        self.menu_buttons = []
        permissions = ROLES.get(self.user['role'], [])
        
        # Menu items: (name, icon, page, required_permission)
        menu_items = [
            ("Dashboard", "📊", 0, None),
            ("New Entry", "📝", 1, "manage_inspections"),
            ("Reports", "📈", 2, "view_reports"),
        ]
        # Fault Management for admin
        if self.user['role'] == 'admin':
            menu_items.append(("Fault Mgmt", "🔧", 3, None))
        # Rework for eligible users
        if 'manage_inspections' in permissions or self.user['role'] in ['admin', 'manager']:
            menu_items.append(("Import Data", "🔨", 4, None))
        
        for name, icon, page, perm in menu_items:
            if perm and perm not in permissions:
                continue
            btn = QPushButton(f"{icon}  {name}")
            btn.setProperty("page", page)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setFixedWidth(120)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #CCCCCC;
                    border: none;
                    font-size: 13px;
                    font-weight: normal;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #0D47A1;
                    color: white;
                }
            """)
            btn.clicked.connect(lambda checked, p=page: self.switch_page(p))
            nav_layout.addWidget(btn)
            self.menu_buttons.append(btn)
        
        # Set default active button
        if self.menu_buttons:
            self.set_active_button(0)
        
        layout.addLayout(nav_layout)
        layout.addStretch()
        
        # User Info Section (Right)
        user_container = QHBoxLayout()
        user_container.setSpacing(15)
        
        user_icon = QLabel("👤")
        user_icon.setStyleSheet("font-size: 20px;")
        user_container.addWidget(user_icon)
        
        user_details = QVBoxLayout()
        user_details.setSpacing(2)
        user_name = QLabel(self.user['full_name'])
        user_name.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        user_details.addWidget(user_name)
        user_role = QLabel(f"Role: {self.user['role'].upper()}")
        user_role.setStyleSheet("color: #B3D4FC; font-size: 10px;")
        user_details.addWidget(user_role)
        user_container.addLayout(user_details)
        
        # Settings/Fault Management Button (admin only)
        if self.user['role'] == 'admin':
            settings_btn = QPushButton("⚙️")
            settings_btn.setCursor(Qt.PointingHandCursor)
            settings_btn.setFixedSize(40, 40)
            settings_btn.setToolTip("Fault Management")
            settings_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
            settings_btn.clicked.connect(self.open_fault_management)
            user_container.addWidget(settings_btn)
        
        # Logout button
        logout_btn = QPushButton("🚪")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setFixedSize(40, 40)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        user_container.addWidget(logout_btn)
        
        layout.addLayout(user_container)
        return top_bar
    
    def set_active_button(self, page_index):
        for i, btn in enumerate(self.menu_buttons):
            if i == page_index:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #0D47A1;
                        color: white;
                        border: none;
                        font-size: 13px;
                        font-weight: bold;
                        border-radius: 8px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #CCCCCC;
                        border: none;
                        font-size: 13px;
                        font-weight: normal;
                        border-radius: 8px;
                    }
                    QPushButton:hover {
                        background-color: #0D47A1;
                        color: white;
                    }
                """)
    def switch_page(self, page_index):
        if page_index >= self.content_area.count():
            return
        self.content_area.setCurrentIndex(page_index)
        self.set_active_button(page_index)
        
        # Refresh data when switching to specific pages
        if page_index == 0:
            self.dashboard_page.refresh_data()
        elif page_index == 1:          # New Entry - no refresh needed (or if needed, implement later)
            # Optional: if you want to clear/reset the form, you can add a method later
            pass
        elif page_index == 2:          # Reports
            if hasattr(self, 'reports_page'):
                self.reports_page.refresh()
        elif page_index == 3 and hasattr(self, 'fault_mgmt_page'):
            self.fault_mgmt_page.refresh_data()
        elif page_index == 4 and hasattr(self, 'rework_page'):
            self.rework_page.refresh()
        
   
    
    def open_fault_management(self):
        if hasattr(self, 'fault_mgmt_page'):
            for i in range(self.content_area.count()):
                if self.content_area.widget(i) == self.fault_mgmt_page:
                    self.switch_page(i)
                    break
        else:
            if self.fault_widget is None or not self.fault_widget.isVisible():
                self.fault_widget = FaultManagementWidget(self.db, self.user)
                self.fault_widget.setWindowTitle("Fault Management System")
                self.fault_widget.setGeometry(100, 100, 1200, 700)
                self.fault_widget.show()
            else:
                self.fault_widget.raise_()
                self.fault_widget.activateWindow()
    
    def on_data_saved(self):
        CustomMessageBox.show_success(self, "Success", "Data saved successfully!")
        self.dashboard_page.refresh_data()
    
    def logout(self):
        reply = CustomMessageBox.show_question(
            self, 
            'Logout Confirmation', 
            'Are you sure you want to logout?\n\nAny unsaved data will be lost.'
        )
        if reply == CustomMessageBox.Accepted:
            CustomMessageBox.show_info(self, 'Logged Out', 'You have been successfully logged out.')
            QTimer.singleShot(500, self.close)
    
    def closeEvent(self, event):
        reply = CustomMessageBox.show_question(
            self,
            'Exit Application',
            'Are you sure you want to exit the application?'
        )
        if reply == CustomMessageBox.Accepted:
            if hasattr(self, 'db'):
                self.db.close()
            event.accept()
        else:
            event.ignore()