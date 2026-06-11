from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QStackedWidget, QFrame,
                             QScrollArea, QApplication, QMessageBox)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from database import Database
from config import APP_CONFIG, ROLES
from widgets.dashboard_widget import DashboardWidget
from widgets.new_entry_widget import NewEntryWidget
from widgets.reports_widget import ReportsWidget
from widgets.fault_management_widget import FaultManagementWidget
from widgets.rework_widget import ReworkWidget
from widgets.users_widget import UsersWidget
from custom_dialogs import CustomMessageBox
from vgotel_loader import VgotelLoader


class MainWindow(QMainWindow):
    logout_signal = pyqtSignal()

    def __init__(self, db: Database, user_data: dict):
        super().__init__()
        self.db = db
        self.user = user_data
        self.user_id = user_data['id']
        self.user_role = user_data['role']
        self.fault_widget = None
        self.is_logging_out = False   # <-- flag to distinguish logout from exit
        
        # ========== INIT ALL ATTRIBUTES FIRST ==========
        self.user_permissions = {}
        self.page_indices = {}
        self.menu_buttons = []
        self.content_area = None
        self.dashboard_page = None
        self.new_entry_page = None
        self.reports_page = None
        self.fault_mgmt_page = None
        self.rework_page = None
        self.users_page = None
        
        self.load_permissions()

        # Show loader
        self.loader = VgotelLoader(duration=3000)
        self.loader.show()
        QApplication.processEvents()

        # Build UI with error handling
        try:
            self.setup_ui()
        except Exception as e:
            print(f"[SETUP_UI ERROR] {e}")
            import traceback
            traceback.print_exc()
            raise

        # Close loader
        self.loader.finish()
        self.showMaximized()
    
    def load_permissions(self):
        if self.user_role == 'admin':
            self.user_permissions = {'*': True}
        else:
            try:
                self.user_permissions = self.db.get_user_permissions_dict(self.user_id)
            except Exception as e:
                print(f"[PERMISSIONS] Error: {e}")
                self.user_permissions = {}
    
    def has_permission(self, function_code: str) -> bool:
        if self.user_role == 'admin' or self.user_permissions.get('*'):
            return True
        return self.user_permissions.get(function_code, False)
    
    def has_page_access(self, route: str) -> bool:
        if self.user_role == 'admin':
            return True
        role_perms = ROLES.get(self.user_role, [])
        route_perm_map = {
            'dashboard': None,
            'inspections': 'manage_inspections',
            'reports': 'view_reports',
            'faults': None,
            'rework': 'manage_inspections',
            'users': None,
        }
        required = route_perm_map.get(route)
        if required and required in role_perms:
            return True
        return any(
            code.startswith(f"{route}_") and allowed 
            for code, allowed in self.user_permissions.items()
        )
    
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
        
        # ========== STEP 1: CREATE CONTENT AREA FIRST ==========
        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet("""
            QStackedWidget {
                background-color: #F5F5F5;
            }
        """)
        
        # ========== STEP 2: ADD ALL PAGES FIRST ==========
        self.page_indices = {}
        current_index = 0
        
        # Dashboard Page - ALWAYS ADD
        try:
            self.dashboard_page = DashboardWidget(self.db)
            self.content_area.addWidget(self.dashboard_page)
            self.page_indices['dashboard'] = current_index
            current_index += 1
        except Exception as e:
            print(f"[DASHBOARD ERROR] {e}")
            fallback = QWidget()
            fallback.setStyleSheet("background: #F5F5F5;")
            self.content_area.addWidget(fallback)
            self.page_indices['dashboard'] = current_index
            current_index += 1
        
        # New Entry Page
        if self.has_page_access('inspections'):
            try:
                self.new_entry_page = NewEntryWidget(self.db, self.user)
                self.new_entry_page.data_saved.connect(self.on_data_saved)
                self.content_area.addWidget(self.new_entry_page)
                self.page_indices['inspections'] = current_index
                current_index += 1
            except Exception as e:
                print(f"[NEW ENTRY ERROR] {e}")
        
        # Reports Page
        if self.has_page_access('reports'):
            try:
                self.reports_page = ReportsWidget(self.db, self.user_role)
                self.content_area.addWidget(self.reports_page)
                self.page_indices['reports'] = current_index
                current_index += 1
            except Exception as e:
                print(f"[REPORTS ERROR] {e}")
        
        # Fault Management Page
        if self.has_page_access('faults'):
            try:
                self.fault_mgmt_page = FaultManagementWidget(self.db, self.user)
                self.content_area.addWidget(self.fault_mgmt_page)
                self.page_indices['faults'] = current_index
                current_index += 1
            except Exception as e:
                print(f"[FAULT MGMT ERROR] {e}")
        
        # Rework Station Page
        if self.has_page_access('rework'):
            try:
                self.rework_page = ReworkWidget(self.db, self.user)
                self.content_area.addWidget(self.rework_page)
                self.page_indices['rework'] = current_index
                current_index += 1
            except Exception as e:
                print(f"[REWORK ERROR] {e}")
        
        # User Management Page - Admin only
        if self.user_role == 'admin':
            try:
                self.users_page = UsersWidget(self.db, self.user_role, self.user_id)
                self.content_area.addWidget(self.users_page)
                self.page_indices['users'] = current_index
                current_index += 1
            except Exception as e:
                print(f"[USERS ERROR] {e}")
        
        # Set default page
        self.content_area.setCurrentIndex(0)
        
        # ========== STEP 3: NOW CREATE TOP BAR (page_indices ready) ==========
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        # ========== STEP 4: ADD CONTENT AREA ==========
        main_layout.addWidget(self.content_area, 1)
    
    def create_top_bar(self):
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
        
        # Logo Section
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
        
        # Navigation Menu
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(5)
        
        self.menu_buttons = []
        
        # Build menu based on available pages in page_indices
        menu_items = []
        
        if 'dashboard' in self.page_indices:
            menu_items.append(("Dashboard", "📊", 'dashboard'))
        if 'inspections' in self.page_indices:
            menu_items.append(("New Entry", "📝", 'inspections'))
        if 'reports' in self.page_indices:
            menu_items.append(("Reports", "📈", 'reports'))
        if 'faults' in self.page_indices:
            menu_items.append(("Fault Mgmt", "🔧", 'faults'))
        if 'rework' in self.page_indices:
            menu_items.append(("Import Data", "🔨", 'rework'))
        if 'users' in self.page_indices:
            menu_items.append(("Users", "👥", 'users'))
        
        for name, icon, route in menu_items:
            page_index = self.page_indices[route]
            
            btn = QPushButton(f"{icon}  {name}")
            btn.setProperty("page", page_index)
            btn.setProperty("route", route)
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
            btn.clicked.connect(lambda checked, p=page_index: self.switch_page(p))
            nav_layout.addWidget(btn)
            self.menu_buttons.append(btn)
        
        # Set default active button
        if self.menu_buttons:
            self.set_active_button(0)
        
        layout.addLayout(nav_layout)
        layout.addStretch()
        
        # User Info Section
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
        user_role = QLabel(f"Role: {self.user_role.upper()}")
        user_role.setStyleSheet("color: #B3D4FC; font-size: 10px;")
        user_details.addWidget(user_role)
        user_container.addLayout(user_details)
        
        # Settings button (admin only)
        if self.user_role == 'admin':
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
        if not self.content_area or page_index >= self.content_area.count():
            return
        
        self.content_area.setCurrentIndex(page_index)
        self.set_active_button(page_index)

        # Find route by index
        route = None
        for r, idx in self.page_indices.items():
            if idx == page_index:
                route = r
                break
        
        # Safely refresh pages
        if route == 'dashboard' and self.dashboard_page is not None:
            try:
                self.dashboard_page.refresh_data()
            except Exception as e:
                print(f"[REFRESH ERROR] Dashboard: {e}")
        elif route == 'reports' and self.reports_page is not None:
            try:
                self.reports_page.refresh()
            except Exception as e:
                print(f"[REFRESH ERROR] Reports: {e}")
        elif route == 'faults' and self.fault_mgmt_page is not None:
            try:
                self.fault_mgmt_page.refresh_data()
            except Exception as e:
                print(f"[REFRESH ERROR] Faults: {e}")
        elif route == 'rework' and self.rework_page is not None:
            try:
                self.rework_page.refresh()
            except Exception as e:
                print(f"[REFRESH ERROR] Rework: {e}")
        elif route == 'users' and self.users_page is not None:
            try:
                self.users_page.load_users()
            except Exception as e:
                print(f"[REFRESH ERROR] Users: {e}")
    
    def open_fault_management(self):
        if self.user_role != 'admin':
            QMessageBox.warning(self, "Access Denied", "Only admin can access Fault Management.")
            return
            
        if 'faults' in self.page_indices:
            self.switch_page(self.page_indices['faults'])
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
        if self.dashboard_page is not None:
            try:
                self.dashboard_page.refresh_data()
            except Exception as e:
                print(f"[REFRESH ERROR] After save: {e}")
    
    def logout(self):
        reply = CustomMessageBox.show_question(
            self, 
            'Logout Confirmation', 
            'Are you sure you want to logout?\n\nAny unsaved data will be lost.'
        )
        if reply == CustomMessageBox.Accepted:
            CustomMessageBox.show_info(self, 'Logged Out', 'You have been successfully logged out.')
            self.is_logging_out = True   # <-- set flag before closing
            self.logout_signal.emit()
            QTimer.singleShot(500, self.close)
    
    
    def closeEvent(self, event):
        # If we are logging out, just accept and do nothing else
        if getattr(self, 'is_logging_out', False):
            event.accept()
            return

        # User clicked the X button (real exit)
        reply = CustomMessageBox.show_question(
            self,
            'Exit Application',
            'Are you sure you want to exit the application?'
        )
        if reply == CustomMessageBox.Accepted:
            # Close database connections
            if hasattr(self, 'db') and self.db is not None:
                try:
                    self.db.close()
                except:
                    pass
            # Tell the application to quit
            QApplication.quit()
            event.accept()
        else:
            event.ignore()