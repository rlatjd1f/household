import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QListWidget, QStackedWidget, QListWidgetItem, QVBoxLayout, 
                             QLabel, QPushButton)
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from database import init_db
from ui.settings_tab import SettingsTab
from ui.budget_tab import BudgetTab
from ui.asset_tab import AssetTab
from ui.ledger_tab import LedgerTab

COMMON_STYLE = """
QWidget { font-family: 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif; font-size: 13px; }
QListWidget { border: none; outline: none; padding-top: 10px; }
QListWidget::item { height: 44px; padding-left: 20px; border-radius: 0px 22px 22px 0px; margin-right: 12px; }
QPushButton { border-radius: 6px; padding: 8px 20px; font-weight: 600; }
QTableWidget, QTreeWidget { border-radius: 8px; outline: none; }
QHeaderView::section { padding: 12px; border: none; font-weight: 600; font-size: 12px; text-transform: uppercase; }
QTableWidget QTableCornerButton::section, QTreeWidget QHeaderView::section { background-color: transparent; border: none; }
QLineEdit, QSpinBox, QDateEdit, QComboBox { border-radius: 6px; padding: 8px 12px; }
"""

LIGHT_STYLE = COMMON_STYLE + """
QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget { background-color: #f8f9fa; border: none; }
#ScrollContent { background-color: #f8f9fa; }
QWidget { color: #3c4043; }
QListWidget { background-color: #ffffff; border-right: 1px solid #dadce0; }
QListWidget::item { color: #5f6368; }
QListWidget::item:selected { background-color: #e8f0fe; color: #1a73e8; }
QListWidget::item:hover:!selected { background-color: #f1f3f4; }
QHeaderView::section { background-color: #ffffff; border-bottom: 2px solid #e8eaed; color: #5f6368; }
QHeaderView::section:vertical { background-color: #ffffff; border-right: 2px solid #e8eaed; }
QTableWidget QTableCornerButton::section { background-color: #ffffff; border-bottom: 2px solid #e8eaed; border-right: 2px solid #e8eaed; }
QTableWidget, QTreeWidget { background-color: #ffffff; border: 1px solid #dadce0; gridline-color: #f1f3f4; selection-background-color: #e8f0fe; selection-color: #1a73e8; outline: none; border-radius: 8px; }
QTableWidget QWidget, QTreeWidget QWidget { background-color: #ffffff; }
QFrame[frameShape="5"] { background-color: #ffffff; border: 1px solid #dadce0; border-radius: 12px; }
QLabel#SummaryLabel { font-weight: 600; font-size: 15px; background-color: #ffffff; border: 1px solid #dadce0; border-radius: 8px; padding: 10px 15px; }
QPushButton { background-color: #1a73e8; color: white; border: 1px solid #1a73e8; }
QPushButton:hover { background-color: #1765cc; }
QPushButton#DeleteBtn { background-color: #f1f3f4; color: #5f6368; border: 1px solid #dadce0; }
QPushButton#DeleteBtn:hover { background-color: #e8eaed; }
QLineEdit, QSpinBox, QDateEdit, QComboBox { background-color: #ffffff; border: 1px solid #dadce0; color: #202124; }
QComboBox { padding: 2px 25px 2px 10px; min-height: 28px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left: 1px solid #dadce0; border-top-right-radius: 6px; border-bottom-right-radius: 6px; background-color: #f1f3f4; }
QComboBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #5f6368; width: 0; height: 0; }
QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus { border: 2px solid #1a73e8; }
QTabWidget::pane { border: 1px solid #dadce0; background: white; }
QTabBar::tab { color: #5f6368; }
QTabBar::tab:selected { color: #1a73e8; border-bottom: 2px solid #1a73e8; }
QMessageBox { background-color: #ffffff; }
QMessageBox QLabel { color: #3c4043; font-size: 14px; }
QMessageBox QPushButton { min-width: 80px; }
"""

DARK_STYLE = COMMON_STYLE + """
QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget { background-color: #202124; border: none; }
#ScrollContent { background-color: #202124; }
QWidget { color: #e8eaed; }
QListWidget { background-color: #2d2e30; border-right: 1px solid #3c4043; }
QListWidget::item { color: #9aa0a6; }
QListWidget::item:selected { background-color: #3c4043; color: #8ab4f8; }
QListWidget::item:hover:!selected { background-color: #35363a; }
QHeaderView::section { background-color: #2d2e30; border-bottom: 2px solid #3c4043; color: #9aa0a6; }
QHeaderView::section:vertical { background-color: #2d2e30; border-right: 1px solid #3c4043; }
QTableWidget QTableCornerButton::section { background-color: #2d2e30; border-bottom: 2px solid #3c4043; border-right: 2px solid #3c4043; }
QTableWidget, QTreeWidget { background-color: #2d2e30; border: 1px solid #3c4043; gridline-color: #3c4043; selection-background-color: #3c4043; selection-color: #8ab4f8; outline: none; border-radius: 8px; }
QTableWidget QWidget, QTreeWidget QWidget { background-color: #2d2e30; }
QFrame[frameShape="5"] { background-color: #2d2e30; border: 1px solid #3c4043; border-radius: 12px; }
QLabel#SummaryLabel { font-weight: 600; font-size: 15px; background-color: #2d2e30; border: 1px solid #3c4043; border-radius: 8px; padding: 10px 15px; }
QPushButton { background-color: #8ab4f8; color: #202124; border: 1px solid #8ab4f8; }
QPushButton:hover { background-color: #aecbfa; }
QPushButton#DeleteBtn { background-color: #3c4043; color: #e8eaed; border: 1px solid #5f6368; }
QPushButton#DeleteBtn:hover { background-color: #4d4d4d; }
QLineEdit, QSpinBox, QDateEdit, QComboBox { background-color: #3c4043; border: 1px solid #5f6368; color: #e8eaed; }
QComboBox { padding: 2px 25px 2px 10px; min-height: 28px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left: 1px solid #5f6368; border-top-right-radius: 6px; border-bottom-right-radius: 6px; background-color: #35363a; }
QComboBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #9aa0a6; width: 0; height: 0; }
QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus { border: 2px solid #8ab4f8; }
QTabWidget::pane { border: 1px solid #3c4043; background: #2d2e30; }
QTabBar::tab { color: #9aa0a6; }
QTabBar::tab:selected { color: #8ab4f8; border-bottom: 2px solid #8ab4f8; }
QMessageBox { background-color: #2d2e30; }
QMessageBox QLabel { color: #e8eaed; font-size: 14px; }
QMessageBox QPushButton { min-width: 80px; }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Household Manager")
        self.resize(2000, 900)
        self.is_dark_mode = False
        init_db()
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Sidebar
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(5)
        
        # Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(10, 0, 10, 0)
        self.theme_btn = QPushButton("🌙 테마")
        self.theme_btn.setFlat(True)
        self.theme_btn.setStyleSheet("font-size: 12px; padding: 8px;")
        self.theme_btn.clicked.connect(self.toggle_theme)
        
        self.import_btn = QPushButton("📂 엑셀 임포트")
        self.import_btn.setFlat(True)
        self.import_btn.setStyleSheet("font-size: 12px; padding: 8px; color: #1a73e8;")
        self.import_btn.clicked.connect(self.handle_excel_import)
        
        btn_row.addWidget(self.theme_btn)
        btn_row.addWidget(self.import_btn)
        sidebar_layout.addLayout(btn_row)

        self.sidebar = QListWidget()
        sidebar_layout.addWidget(self.sidebar)
        main_layout.addWidget(sidebar_container)

        # Content
        content_container = QVBoxLayout()
        content_container.setContentsMargins(30, 20, 30, 20)
        self.content_stack = QStackedWidget()
        content_container.addWidget(self.content_stack)
        main_layout.addLayout(content_container)

        self.setup_pages()
        self.setup_sidebar()
        self.sidebar.currentRowChanged.connect(self.handle_navigation)
        self.sidebar.setCurrentRow(0)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        QApplication.instance().setStyleSheet(DARK_STYLE if self.is_dark_mode else LIGHT_STYLE)
        self.theme_btn.setText("☀️ 테마" if self.is_dark_mode else "🌙 테마")

    def handle_excel_import(self):
        from PyQt6.QtWidgets import QFileDialog
        from ui.migration_util import import_from_excel
        file_path, _ = QFileDialog.getOpenFileName(self, "엑셀 가져오기", "", "Excel Files (*.xlsx *.xls)")
        if file_path and import_from_excel(file_path, self):
            for i in range(self.content_stack.count()):
                w = self.content_stack.widget(i)
                if hasattr(w, 'load_data'): w.load_data()
                if hasattr(w, 'refresh_data'): w.refresh_data()

    def setup_pages(self):
        self.pages = {'settings': SettingsTab(), 'budget': BudgetTab(), 'asset': AssetTab()}
        self.month_pages = {m: LedgerTab(month=m) for m in range(1, 13)}
        self.content_stack.addWidget(self.pages['settings'])
        self.content_stack.addWidget(self.pages['budget'])
        self.content_stack.addWidget(self.pages['asset'])
        for m in range(1, 13): self.content_stack.addWidget(self.month_pages[m])

    def setup_sidebar(self):
        self.sidebar.addItem(QListWidgetItem("⚙️  설정"))
        self.sidebar.addItem(QListWidgetItem("📊  예산 설정"))
        self.sidebar.addItem(QListWidgetItem("💰  자산 설정"))
        h = QListWidgetItem("📅  월별 가계부")
        h.setFlags(Qt.ItemFlag.NoItemFlags)
        self.sidebar.addItem(h)
        for i in range(1, 13): self.sidebar.addItem(QListWidgetItem(f"      {i}월"))

    def handle_navigation(self, row):
        idx = -1
        if 0 <= row <= 2: idx = row
        elif 4 <= row <= 15: idx = 3 + (row - 4)
        if idx != -1:
            self.content_stack.setCurrentIndex(idx)
            w = self.content_stack.currentWidget()
            if hasattr(w, 'load_data'): w.load_data()
            if hasattr(w, 'refresh_data'): w.refresh_data()

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(LIGHT_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
