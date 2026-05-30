# main.py - CORRECTED VERSION
import fix_all  # MUST BE THE FIRST IMPORT

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from login import LoginDialog

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    
    # Set application style
    app.setStyle('Fusion')
    
    # Apply global stylesheet
    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI';
        }
        QMessageBox {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QMessageBox QPushButton {
            background-color: #0f3460;
            color: white;
            padding: 8px 16px;
            border-radius: 5px;
            min-width: 80px;
        }
        QMessageBox QPushButton:hover {
            background-color: #00a8ff;
        }
    """)
    
    # Show login window
    login_window = LoginDialog()
    login_window.show()
    
    sys.exit(app.exec_())