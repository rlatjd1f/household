import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QListWidget, QStackedWidget, QListWidgetItem, QVBoxLayout, QLabel)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont
from database import init_db
from ui.settings_tab import SettingsTab
from ui.budget_tab import BudgetTab
from ui.asset_tab import AssetTab
from ui.ledger_tab import LedgerTab

GOOGLE_STYLE = """
QMainWindow {
    background-color: #f8f9fa;
}

/* Global Font and Text */
QWidget {
    font-family: 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
    font-size: 13px;
    color: #3c4043;
}

/* Sidebar Styling */
QListWidget {
    background-color: #ffffff;
    border: none;
    border-right: 1px solid #dadce0;
    outline: none;
    padding-top: 10px;
}

QListWidget::item {
    height: 44px;
    padding-left: 20px;
    border-radius: 0px 22px 22px 0px;
    margin-right: 12px;
    color: #5f6368;
}

QListWidget::item:selected {
    background-color: #e8f0fe;
    color: #1a73e8;
    font-weight: 600;
}

QListWidget::item:hover:!selected {
    background-color: #f1f3f4;
    color: #202124;
}

/* Content Area */
QStackedWidget {
    background-color: #f8f9fa;
}

/* Buttons */
QPushButton {
    background-color: #1a73e8;
    color: white;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 13px;
    border: 1px solid #1a73e8;
}

QPushButton:hover {
    background-color: #1765cc;
    border-color: #1765cc;
}

QPushButton:pressed {
    background-color: #1557b0;
}

QPushButton:disabled {
    background-color: #dadce0;
    border-color: #dadce0;
    color: #9aa0a6;
}

/* Tables */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #dadce0;
    gridline-color: #f1f3f4;
    border-radius: 8px;
    selection-background-color: #e8f0fe;
    selection-color: #1a73e8;
    outline: none;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #f1f3f4;
}

QHeaderView::section {
    background-color: #ffffff;
    padding: 12px;
    border: none;
    border-bottom: 2px solid #e8eaed;
    color: #5f6368;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

/* Input Fields (Universal) */
QLineEdit, QSpinBox, QDateEdit, QComboBox {
    background-color: #ffffff;
    border: 1px solid #dadce0;
    border-radius: 6px;
    padding: 8px 12px;
    color: #202124;
    selection-background-color: #1a73e8;
    selection-color: #ffffff;
}

QLineEdit:hover, QSpinBox:hover, QDateEdit:hover, QComboBox:hover {
    border-color: #bdc1c6;
}

QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus {
    border: 2px solid #1a73e8;
    padding: 7px 11px;
}

/* Specific for QSpinBox/QDateEdit buttons */
QSpinBox::up-button, QDateEdit::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #dadce0;
    border-top-right-radius: 6px;
    background: #f8f9fa;
}

QSpinBox::down-button, QDateEdit::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid #dadce0;
    border-bottom-right-radius: 6px;
    background: #f8f9fa;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #f1f3f4;
}

QSpinBox::up-arrow, QDateEdit::up-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #5f6368;
    width: 0; height: 0;
}

QSpinBox::down-arrow, QDateEdit::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #5f6368;
    width: 0; height: 0;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #f8f9fa;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #dadce0;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #bdc1c6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #dadce0;
    background: white;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background: transparent;
    border: none;
    padding: 12px 24px;
    color: #5f6368;
    font-weight: 500;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:hover {
    background: #f1f3f4;
}

QTabBar::tab:selected {
    color: #1a73e8;
    border-bottom: 2px solid #1a73e8;
    font-weight: 600;
}

/* Labels */
QLabel {
    color: #3c4043;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Household Manager")
        self.resize(1400, 900)
        
        init_db()
        
        # Main Layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 1. Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(240)
        
        # Menu Setup
        self.setup_sidebar()
        main_layout.addWidget(self.sidebar)

        # 2. Content
        content_container = QVBoxLayout()
        content_container.setContentsMargins(30, 20, 30, 20)
        self.content_stack = QStackedWidget()
        content_container.addWidget(self.content_stack)
        main_layout.addLayout(content_container)

        # Initialize Pages
        self.pages = {}
        
        # Basic Pages
        self.pages['settings'] = SettingsTab()
        self.pages['budget'] = BudgetTab()
        self.pages['asset'] = AssetTab()
        
        # Ledger Pages (12 months)
        self.month_pages = {}
        for m in range(1, 13):
            page = LedgerTab(month=m)
            self.month_pages[m] = page
            
        # Add to stack
        self.content_stack.addWidget(self.pages['settings']) # Index 0
        self.content_stack.addWidget(self.pages['budget'])   # Index 1
        self.content_stack.addWidget(self.pages['asset'])    # Index 2
        
        for m in range(1, 13):
            self.content_stack.addWidget(self.month_pages[m]) # Index 3-14

        self.sidebar.currentRowChanged.connect(self.handle_navigation)
        
        # Default to current month
        import datetime
        current_month = datetime.datetime.now().month
        # Row mapping: 0:Menu, 1:Settings, 2:Budget, 3:Asset, 4:Spacer, 5:LedgerHeader, 6:Jan, 7:Feb...
        self.sidebar.setCurrentRow(6 + (current_month - 1))

    def setup_sidebar(self):
        # Header: Menu
        menu_header = QListWidgetItem("📋  MENU")
        menu_header.setFlags(Qt.ItemFlag.NoItemFlags)
        self.sidebar.addItem(menu_header)
        
        self.sidebar.addItem(QListWidgetItem("⚙️  설정"))     # Row 1
        self.sidebar.addItem(QListWidgetItem("📊  예산 설정")) # Row 2
        self.sidebar.addItem(QListWidgetItem("💰  자산 설정")) # Row 3
        
        # Spacer
        self.sidebar.addItem(QListWidgetItem(""))            # Row 4
        
        # Header: Monthly
        ledger_header = QListWidgetItem("📅  월별 가계부")
        ledger_header.setFlags(Qt.ItemFlag.NoItemFlags)
        self.sidebar.addItem(ledger_header) # Row 5
        
        # Months 1-12
        for i in range(1, 13):
            self.sidebar.addItem(QListWidgetItem(f"      {i}월 내역")) # Row 6-17

    def handle_navigation(self, row):
        # Map Sidebar rows to StackedWidget indices
        # row 1-3 -> index 0-2
        # row 6-17 -> index 3-14
        
        target_index = -1
        if 1 <= row <= 3:
            target_index = row - 1
        elif 6 <= row <= 17:
            target_index = 3 + (row - 6)
            
        if target_index != -1:
            self.content_stack.setCurrentIndex(target_index)
            widget = self.content_stack.currentWidget()
            if hasattr(widget, 'load_data'): widget.load_data()
            if hasattr(widget, 'refresh_data'): widget.refresh_data()

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(GOOGLE_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
