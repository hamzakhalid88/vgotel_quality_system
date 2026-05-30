from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame,
                             QApplication)
from PyQt5.QtCore import Qt, pyqtSignal
from database import Database

class LoginDialog(QDialog):
    login_successful = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Login - Quality Control System")
        self.setFixedSize(450, 550)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
        
        # Main frame
        main_frame = QFrame()
        main_frame.setObjectName("login_frame")
        main_frame.setStyleSheet("""
            QFrame#login_frame {
                background-color: #1E1E1E;
                border-radius: 15px;
                border: 2px solid #0D47A1;
            }
        """)
        
        # Frame layout
        frame_layout = QVBoxLayout()
        frame_layout.setSpacing(0)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        main_frame.setLayout(frame_layout)
        
        # Header section with blue bar
        header_widget = QFrame()
        header_widget.setStyleSheet("""
            QFrame {
                background-color: #0D47A1;
                border-top-left-radius: 13px;
                border-top-right-radius: 13px;
            }
        """)
        header_widget.setFixedHeight(80)
        header_layout = QVBoxLayout()
        header_widget.setLayout(header_layout)
        
        title = QLabel("QUALITY CONTROL SYSTEM")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            font-family: 'Segoe UI';
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Quality Management Professional Suite")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 11px;
            color: #B3D4FC;
            font-family: 'Segoe UI';
        """)
        header_layout.addWidget(subtitle)
        
        frame_layout.addWidget(header_widget)
        
        # Content section
        content_widget = QFrame()
        content_widget.setStyleSheet("background-color: #1E1E1E;")
        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(50, 40, 50, 40)
        content_widget.setLayout(content_layout)
        
        # Welcome text
        welcome = QLabel("Welcome Back")
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #FFFFFF;
            font-family: 'Segoe UI';
        """)
        content_layout.addWidget(welcome)
        
        # Instruction
        instruction = QLabel("Please enter your credentials to continue")
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setStyleSheet("""
            font-size: 12px;
            color: #888888;
            margin-bottom: 10px;
        """)
        content_layout.addWidget(instruction)
        
        content_layout.addSpacing(10)
        
        # Username field container
        username_container = QVBoxLayout()
        username_container.setSpacing(8)
        
        username_label = QLabel("Username")
        username_label.setStyleSheet("""
            color: #0D47A1;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        username_container.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setMinimumHeight(42)
        self.username_input.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D30;
                color: #FFFFFF;
                border: 1px solid #3E3E42;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #0D47A1;
            }
        """)
        username_container.addWidget(self.username_input)
        content_layout.addLayout(username_container)
        
        # Password field container
        password_container = QVBoxLayout()
        password_container.setSpacing(8)
        
        password_label = QLabel("Password")
        password_label.setStyleSheet("""
            color: #0D47A1;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        password_container.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(42)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D30;
                color: #FFFFFF;
                border: 1px solid #3E3E42;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #0D47A1;
            }
        """)
        password_container.addWidget(self.password_input)
        content_layout.addLayout(password_container)
        
        content_layout.addSpacing(20)
        
        # Buttons container
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        self.login_btn = QPushButton("LOGIN")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setMinimumHeight(42)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0D47A1;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0A3A7A;
            }
        """)
        self.login_btn.clicked.connect(self.authenticate)
        
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setMinimumHeight(42)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E3E42;
                color: #E0E0E0;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4E4E52;
                color: white;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.login_btn)
        buttons_layout.addWidget(cancel_btn)
        content_layout.addLayout(buttons_layout)
        
        frame_layout.addWidget(content_widget)
        
        # Footer section
        footer_widget = QFrame()
        footer_widget.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-bottom-left-radius: 13px;
                border-bottom-right-radius: 13px;
            }
        """)
        footer_widget.setFixedHeight(50)
        footer_layout = QHBoxLayout()
        footer_widget.setLayout(footer_layout)
        
        version = QLabel("Version 2.0")
        version.setStyleSheet("color: #666666; font-size: 10px;")
        footer_layout.addWidget(version)
        
        footer_layout.addStretch()
        
        company = QLabel("© Professional Solutions")
        company.setStyleSheet("color: #666666; font-size: 10px;")
        footer_layout.addWidget(company)
        
        frame_layout.addWidget(footer_widget)
        
        # Add to main layout
        main_layout.addWidget(main_frame)
        
        # Close button (X)
        close_btn = QPushButton("✕")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #F44336;
            }
        """)
        close_btn.clicked.connect(self.close)
        close_btn.setParent(self)
        close_btn.resize(35, 35)
        close_btn.move(self.width() - 45, 12)
        
        # Set focus
        self.username_input.setFocus()
        
        # Enter key navigation
        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.authenticate)
    
    def authenticate(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Warning", "Please enter username and password")
            return
        
        try:
            user = self.db.authenticate_user(username, password)
            
            if user:
                self.db.update_last_login(user['id'])
                self.login_successful.emit(user)
                
                from main_window import MainWindow
                self.main_window = MainWindow(self.db, user)
                self.main_window.show()
                self.close()
            else:
                QMessageBox.critical(self, "Error", "Invalid username or password")
                self.password_input.clear()
                self.password_input.setFocus()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login error: {str(e)}")
    
    def resizeEvent(self, event):
        for btn in self.findChildren(QPushButton):
            if btn.text() == "✕":
                btn.move(self.width() - 45, 12)
                break
        super().resizeEvent(event)