from PyQt5.QtGui import QPalette, QColor
from config import APP_CONFIG

def apply_style(app):
    """Apply professional dark theme"""
    app.setStyleSheet("""
        QMainWindow {
            background-color: #1E1E1E;
        }
        QLabel#header {
            background-color: #0D47A1;
            color: white;
            font-size: 24px;
            font-weight: bold;
            padding: 15px;
        }
        QTabWidget::pane {
            border: 1px solid #2B2B2B;
            background-color: #252526;
        }
        QTabBar::tab {
            background-color: #2B2B2B;
            color: #CCCCCC;
            padding: 10px 20px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #0D47A1;
            color: white;
        }
        QPushButton {
            background-color: #0D47A1;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #1565C0;
        }
        QLineEdit, QTextEdit, QComboBox {
            background-color: #3E3E42;
            color: #E0E0E0;
            border: 1px solid #5A5A5E;
            border-radius: 4px;
            padding: 6px;
        }
        QTableWidget {
            background-color: #252526;
            color: #E0E0E0;
            gridline-color: #3E3E42;
        }
        QHeaderView::section {
            background-color: #2D2D30;
            color: #E0E0E0;
            padding: 8px;
            border: 1px solid #3E3E42;
        }
    """)
    
def apply_dark_theme(app):
    """Apply dark theme variant"""
    colors = APP_CONFIG['theme_colors']
    
    style = f"""
    QMainWindow, QDialog {{
        background-color: #1E1E1E;
    }}
    
    QWidget {{
        background-color: #252526;
        color: #E0E0E0;
    }}
    
    QPushButton {{
        background-color: {colors['primary']};
        color: white;
    }}
    
    QLineEdit, QTextEdit, QComboBox {{
        background-color: #3E3E42;
        color: #E0E0E0;
        border: 1px solid #5A5A5E;
    }}
    
    QTableWidget {{
        background-color: #252526;
        color: #E0E0E0;
        gridline-color: #3E3E42;
    }}
    
    QHeaderView::section {{
        background-color: #2D2D30;
        color: #E0E0E0;
    }}
    
    QGroupBox {{
        background-color: #2D2D30;
        border-color: #3E3E42;
        color: #E0E0E0;
    }}
    
    QLabel {{
        color: #E0E0E0;
    }}
    """
    
    app.setStyleSheet(style)