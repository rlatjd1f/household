import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QListWidget, QStackedWidget, QListWidgetItem, QVBoxLayout, 
                             QLabel, QPushButton)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont
from database import init_db
from ui.settings_tab import SettingsTab
from ui.budget_tab import BudgetTab
from ui.asset_tab import AssetTab
from ui.ledger_tab import LedgerTab

COMMON_STYLE = """
/* Global Font and Text */
QWidget {
    font-family: 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
    font-size: 13px;
}

QListWidget {
    border: none;
    outline: none;
    padding-top: 10px;
}

QListWidget::item {
    height: 44px;
    padding-left: 20px;
    border-radius: 0px 22px 22px 0px;
    margin-right: 12px;
}

QPushButton {
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: 600;
}

QTableWidget {
    border-radius: 8px;
    outline: none;
}

QHeaderView::section {
    padding: 12px;
    border: none;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

/* Fix for black corners/headers in some themes */
QTableWidget QTableCornerButton::section, 
QTreeWidget QHeaderView::section {
    background-color: transparent;
    border: none;
}

QLineEdit, QSpinBox, QDateEdit, QComboBox {
    border-radius: 6px;
    padding: 8px 12px;
}
"""

LIGHT_STYLE = COMMON_STYLE + """
QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget { background-color: #f8f9fa; border: none; }
#ScrollContent { background-color: #f8f9fa; }
QWidget { color: #3c4043; }
QListWidget { background-color: #ffffff; border-right: 1px solid #dadce0; }
QListWidget::item { color: #5f6368; }
QListWidget::item:selected { background-color: #e8f0fe; color: #1a73e8; }
QListWidget::item:hover:!selected { background-color: #f1f3f4; }

/* Table/Tree Headers */
QHeaderView::section { background-color: #ffffff; border-bottom: 2px solid #e8eaed; color: #5f6368; }
QHeaderView::section:vertical { background-color: #ffffff; border-right: 2px solid #e8eaed; }
QTableWidget QTableCornerButton::section { background-color: #ffffff; border-bottom: 2px solid #e8eaed; border-right: 2px solid #e8eaed; }

/* Cards in Settings/etc */
QFrame[frameShape="5"] { background-color: #ffffff; border: 1px solid #dadce0; border-radius: 12px; }

QLabel#SummaryLabel {
    font-weight: 600;
    font-size: 15px;
    background-color: #ffffff;
    border: 1px solid #dadce0;
    border-radius: 8px;
    padding: 10px 15px;
}

QPushButton { background-color: #1a73e8; color: white; border: 1px solid #1a73e8; }
QPushButton:hover { background-color: #1765cc; }
QPushButton#DeleteBtn { background-color: #f1f3f4; color: #5f6368; border: 1px solid #dadce0; }
QPushButton#DeleteBtn:hover { background-color: #e8eaed; }

QTableWidget, QTreeWidget { background-color: #ffffff; border: 1px solid #dadce0; gridline-color: #f1f3f4; selection-background-color: #e8f0fe; selection-color: #1a73e8; outline: none; border-radius: 8px; }
QHeaderView::section { background-color: #ffffff; border-bottom: 2px solid #e8eaed; color: #5f6368; }

QLineEdit, QSpinBox, QDateEdit, QComboBox { background-color: #ffffff; border: 1px solid #dadce0; color: #202124; }
QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus { border: 2px solid #1a73e8; }

QTabWidget::pane { border: 1px solid #dadce0; background: white; }
QTabBar::tab { color: #5f6368; }
QTabBar::tab:selected { color: #1a73e8; border-bottom: 2px solid #1a73e8; }
"""

DARK_STYLE = COMMON_STYLE + """
QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget { background-color: #202124; border: none; }
#ScrollContent { background-color: #202124; }
QWidget { color: #e8eaed; }
QListWidget { background-color: #2d2e30; border-right: 1px solid #3c4043; }
QListWidget::item { color: #9aa0a6; }
QListWidget::item:selected { background-color: #3c4043; color: #8ab4f8; }
QListWidget::item:hover:!selected { background-color: #35363a; }

/* Table/Tree Headers */
QHeaderView::section { background-color: #2d2e30; border-bottom: 2px solid #3c4043; color: #9aa0a6; }
QHeaderView::section:vertical { background-color: #2d2e30; border-right: 2px solid #3c4043; }
QTableWidget QTableCornerButton::section { background-color: #2d2e30; border-bottom: 2px solid #3c4043; border-right: 2px solid #3c4043; }

/* Cards in Settings/etc */
QFrame[frameShape="5"] { background-color: #2d2e30; border: 1px solid #3c4043; border-radius: 12px; }

QLabel#SummaryLabel {
    font-weight: 600;
    font-size: 15px;
    background-color: #2d2e30;
    border: 1px solid #3c4043;
    border-radius: 8px;
    padding: 10px 15px;
}

QPushButton { background-color: #8ab4f8; color: #202124; border: 1px solid #8ab4f8; }
QPushButton:hover { background-color: #aecbfa; }
QPushButton#DeleteBtn { background-color: #3c4043; color: #e8eaed; border: 1px solid #5f6368; }
QPushButton#DeleteBtn:hover { background-color: #4d4d4d; }

QTableWidget, QTreeWidget { background-color: #2d2e30; border: 1px solid #3c4043; gridline-color: #3c4043; selection-background-color: #3c4043; selection-color: #8ab4f8; outline: none; border-radius: 8px; }
QHeaderView::section { background-color: #2d2e30; border-bottom: 2px solid #3c4043; color: #9aa0a6; }

QLineEdit, QSpinBox, QDateEdit, QComboBox { background-color: #3c4043; border: 1px solid #5f6368; color: #e8eaed; }
QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus { border: 2px solid #8ab4f8; }

QTabWidget::pane { border: 1px solid #3c4043; background: #2d2e30; }
QTabBar::tab { color: #9aa0a6; }
QTabBar::tab:selected { color: #8ab4f8; border-bottom: 2px solid #8ab4f8; }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Household Manager")
        self.resize(2000, 900) # Expanded width
        self.is_dark_mode = False
        
        init_db()
        
        # Main Layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 1. Sidebar Container
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(5)
        
        # Theme Toggle Button at top of sidebar
        self.theme_btn = QPushButton("🌙 다크 모드 전환")
        self.theme_btn.setFlat(True)
        self.theme_btn.setStyleSheet("margin: 10px; padding: 12px; text-align: left; font-size: 14px;")
        self.theme_btn.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.theme_btn)

        # Sidebar List (Contains Menu items)
        self.sidebar = QListWidget()
        sidebar_layout.addWidget(self.sidebar)

        main_layout.addWidget(sidebar_container)

        # 2. Content
        content_container = QVBoxLayout()
        content_container.setContentsMargins(30, 20, 30, 20)
        self.content_stack = QStackedWidget()
        content_container.addWidget(self.content_stack)
        main_layout.addLayout(content_container)

        # Initialize Pages
        self.setup_pages()
        self.setup_sidebar()

        self.sidebar.currentRowChanged.connect(self.handle_navigation)
        
        # Default to current month
        import datetime
        current_month = datetime.datetime.now().month
        # Row 4 is Jan, 5 is Feb...
        self.sidebar.setCurrentRow(4 + (current_month - 1))

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            QApplication.instance().setStyleSheet(DARK_STYLE)
            self.theme_btn.setText("☀️ 라이트 모드 전환")
        else:
            QApplication.instance().setStyleSheet(LIGHT_STYLE)
            self.theme_btn.setText("🌙 다크 모드 전환")

    def setup_pages(self):
        self.pages = {'settings': SettingsTab(), 'budget': BudgetTab(), 'asset': AssetTab()}
        self.month_pages = {m: LedgerTab(month=m) for m in range(1, 13)}
        
        self.content_stack.addWidget(self.pages['settings'])
        self.content_stack.addWidget(self.pages['budget'])
        self.content_stack.addWidget(self.pages['asset'])
        for m in range(1, 13):
            self.content_stack.addWidget(self.month_pages[m])

    def setup_sidebar(self):
        # Items directly
        self.sidebar.addItem(QListWidgetItem("⚙️  설정"))     # Row 0
        self.sidebar.addItem(QListWidgetItem("📊  예산 설정")) # Row 1
        self.sidebar.addItem(QListWidgetItem("💰  자산 설정")) # Row 2
        
        # Spacer
        spacer = QListWidgetItem("")
        spacer.setFlags(Qt.ItemFlag.NoItemFlags)
        self.sidebar.addItem(spacer) # Row 3
        
        # Months 1-12
        for i in range(1, 13):
            self.sidebar.addItem(QListWidgetItem(f"      {i}월 내역")) # Row 4-15

    def handle_navigation(self, row):
        target_index = -1
        if 0 <= row <= 2: 
            target_index = row
        elif 4 <= row <= 15: 
            target_index = 3 + (row - 4)
            
        if target_index != -1:
            self.content_stack.setCurrentIndex(target_index)
            widget = self.content_stack.currentWidget()
            if hasattr(widget, 'load_data'): widget.load_data()
            if hasattr(widget, 'refresh_data'): widget.refresh_data()

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(LIGHT_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
