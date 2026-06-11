import fix_all  # MUST BE THE FIRST IMPORT

import sys
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from login import LoginDialog
from main_window import MainWindow
from database import Database


class AppController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.app.setFont(QFont("Segoe UI", 10))
        self.app.setStyle('Fusion')
        self.app.setStyleSheet("""
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

        self.db = None
        self.main_window = None
        self.restarting = False

    def run(self):
        print("[Controller] Starting application...")
        self.show_login()
        sys.exit(self.app.exec_())

    def show_login(self):
        print("[Controller] show_login() called")
        # Clean up previous main window (if any)
        if self.main_window:
            print("[Controller] Cleaning up existing main window")
            self.main_window.close()
            self.main_window.deleteLater()
            self.main_window = None

        if self.db:
            print("[Controller] Closing existing database connection")
            self.db.close()
            self.db = None

        # Create login dialog
        login = LoginDialog()
        print("[Controller] Login dialog created")

        # Force it to be on top and modal
        login.setWindowFlags(login.windowFlags() | Qt.WindowStaysOnTopHint)
        login.setModal(True)
        login.show()
        login.raise_()
        login.activateWindow()
        print(f"[Controller] Login dialog visible: {login.isVisible()}")

        # Execute modally
        result = login.exec_()
        print(f"[Controller] Login dialog exec_() returned: {result}")

        if result == QDialog.Accepted:
            user = login.get_user()
            if user is None:
                print("[Controller] ERROR: get_user() returned None")
                self.show_login()  # try again
                return
            print(f"[Controller] User logged in: {user['username']}")
            self.db = Database()
            self.show_main_window(user)
        else:
            print("[Controller] Login rejected or closed → exiting application")
            self.app.quit()

    def show_main_window(self, user):
        print("[Controller] Showing main window")
        self.main_window = MainWindow(self.db, user)
        self.main_window.logout_signal.connect(self.on_logout)
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def on_logout(self):
        if self.restarting:
            print("[Controller] Already restarting, ignoring logout")
            return
        self.restarting = True
        print("[Controller] Logout signal received, closing main window...")

        if self.main_window:
            self.main_window.close()
            self.main_window.deleteLater()
            self.main_window = None

        if self.db:
            self.db.close()
            self.db = None

        print("[Controller] Scheduling show_login after 800ms")
        QTimer.singleShot(800, self._show_login_after_logout)

    def _show_login_after_logout(self):
        self.restarting = False
        print("[Controller] Now showing login again")
        self.show_login()


if __name__ == "__main__":
    controller = AppController()
    controller.run()