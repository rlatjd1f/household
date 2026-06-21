import sys
import os

# --- macOS Standalone App Crash Workaround ---
if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
    os.environ['QT_MAC_WANTS_LAYER'] = '1'
    # Ensure standard backend for matplotlib on macOS
    os.environ['MPLBACKEND'] = 'Agg' 

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QListWidget, QStackedWidget, QListWidgetItem, QVBoxLayout, 
                             QLabel, QPushButton, QInputDialog, QMessageBox, QFrame,
                             QDialog, QProgressBar)
from PyQt6.QtCore import QSize, Qt, QTimer, QObject, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon
from database import init_db, get_households, add_household, delete_household, update_household_name
from ui.settings_tab import SettingsTab
from ui.budget_tab import BudgetTab
from ui.asset_tab import AssetTab
from ui.ledger_tab import LedgerTab
from ui.report_tab import MonthlyReportTab, YearlyReportTab
from updater import check_for_update, install_update
from version import APP_VERSION

def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

APP_ICON_PATH = resource_path(os.path.join("assets", "icon", "app.ico"))

UI_FONT_FAMILY = "'Malgun Gothic', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif" if sys.platform == "win32" else "'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif"

COMMON_STYLE = """
QWidget { font-family: __UI_FONT_FAMILY__; font-size: 13px; }
QListWidget { border: none; outline: none; padding-top: 10px; }
QListWidget::item { height: 44px; padding-left: 20px; border-radius: 0px 22px 22px 0px; margin-right: 12px; }
QPushButton { border-radius: 6px; padding: 8px 20px; font-weight: 600; }
QTableWidget, QTreeWidget { border-radius: 8px; outline: none; }
QHeaderView::section { padding: 12px; border: none; font-weight: 600; font-size: 12px; text-transform: uppercase; }
QTableWidget QTableCornerButton::section, QTreeWidget QHeaderView::section { background-color: transparent; border: none; }
QLineEdit, QSpinBox, QDateEdit, QComboBox { border-radius: 6px; padding: 8px 12px; }
""".replace("__UI_FONT_FAMILY__", UI_FONT_FAMILY)

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
QTableWidget, QTreeWidget { background-color: #ffffff; border: 1px solid #dadce0; gridline-color: #f1f3f4; selection-background-color: #e8f0fe; selection-color: #1a73e8; outline: none; border-radius: 8px; }
QTableWidget QWidget, QTreeWidget QWidget { background-color: #ffffff; }
QFrame[frameShape="5"], #ContentCard { background-color: #ffffff; border: 1px solid #dadce0; border-radius: 12px; }
QLabel#SummaryLabel { font-weight: 600; font-size: 15px; background-color: #ffffff; border: 1px solid #dadce0; border-radius: 8px; padding: 10px 15px; }
QPushButton { background-color: #1a73e8; color: white; border: 1px solid #1a73e8; }
QPushButton:hover { background-color: #1765cc; }
QPushButton#DeleteBtn { background-color: #f1f3f4; color: #5f6368; border: 1px solid #dadce0; }
QPushButton#SaveBtn { font-size: 16px; background: transparent; border: none; }
QPushButton#SaveBtn:hover { background-color: #f1f3f4; border-radius: 15px; }

QPushButton#MonthBtn {
    background-color: #f1f3f4;
    color: #5f6368;
    border: none;
    border-radius: 20px;
    padding: 8px 15px;
    font-weight: 500;
}
QPushButton#MonthBtn:hover {
    background-color: #e8eaed;
}
QPushButton#MonthBtn[active="true"] {
    background-color: #1a73e8;
    color: white;
    font-weight: bold;
}
QLineEdit, QSpinBox, QDateEdit, QComboBox { background-color: #ffffff; border: 1px solid #dadce0; color: #202124; }
QComboBox QAbstractItemView { 
    background-color: #ffffff; 
    color: #202124; 
    border: 1px solid #dadce0; 
    selection-background-color: #e8f0fe; 
    selection-color: #1a73e8; 
    outline: none;
    padding: 0px;
    margin: 0px;
}
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left: 1px solid #dadce0; border-top-right-radius: 6px; border-bottom-right-radius: 6px; background-color: #f1f3f4; }
QComboBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #5f6368; width: 0; height: 0; }
QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus { border: 2px solid #1a73e8; }
QTabWidget::pane { border: 1px solid #dadce0; background: white; }
QTabBar::tab:selected { color: #1a73e8; border-bottom: 2px solid #1a73e8; }
QMessageBox { background-color: #ffffff; }
QMessageBox QLabel { color: #3c4043; font-size: 14px; }
QMessageBox QPushButton { min-width: 80px; }
QInputDialog { background-color: #ffffff; }
QInputDialog QLabel { color: #3c4043; font-size: 14px; }
QInputDialog QSpinBox { background-color: #ffffff; border: 1px solid #dadce0; color: #202124; border-radius: 6px; padding: 8px 12px; }
QInputDialog QPushButton { min-width: 80px; }
QColorDialog { background-color: #ffffff; color: #3c4043; }
QColorDialog QLabel { color: #3c4043; }
QColorDialog QFrame { background-color: #ffffff; }
QColorDialog QLineEdit, QColorDialog QSpinBox { background-color: #ffffff; border: 1px solid #dadce0; color: #202124; border-radius: 6px; padding: 6px 10px; }
QColorDialog QPushButton { min-width: 80px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px 4px 2px; }
QScrollBar::handle:vertical { background: #c6cbd1; border-radius: 4px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: #9aa0a6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: transparent; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px 4px 2px 4px; }
QScrollBar::handle:horizontal { background: #c6cbd1; border-radius: 4px; min-width: 32px; }
QScrollBar::handle:horizontal:hover { background: #9aa0a6; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: transparent; border: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
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
QTableWidget, QTreeWidget { background-color: #2d2e30; border: 1px solid #3c4043; gridline-color: #3c4043; selection-background-color: #3c4043; selection-color: #8ab4f8; outline: none; border-radius: 8px; }
QTableWidget QWidget, QTreeWidget QWidget { background-color: #2d2e30; }
QFrame[frameShape="5"], #ContentCard { background-color: #2d2e30; border: 1px solid #3c4043; border-radius: 12px; }
QLabel#SummaryLabel { font-weight: 600; font-size: 15px; background-color: #2d2e30; border: 1px solid #3c4043; border-radius: 8px; padding: 10px 15px; }
QPushButton { background-color: #8ab4f8; color: #202124; border: 1px solid #8ab4f8; }
QPushButton:hover { background-color: #aecbfa; }
QPushButton#DeleteBtn { background-color: #3c4043; color: #e8eaed; border: 1px solid #5f6368; }
QPushButton#SaveBtn { font-size: 16px; background: transparent; border: none; }
QPushButton#SaveBtn:hover { background-color: #3c4043; border-radius: 15px; }

QPushButton#MonthBtn {
    background-color: #3c4043;
    color: #9aa0a6;
    border: none;
    border-radius: 20px;
    padding: 8px 15px;
    font-weight: 500;
}
QPushButton#MonthBtn:hover {
    background-color: #4d4d4d;
}
QPushButton#MonthBtn[active="true"] {
    background-color: #8ab4f8;
    color: #202124;
    font-weight: bold;
}
QLineEdit, QSpinBox, QDateEdit, QComboBox { background-color: #3c4043; border: 1px solid #5f6368; color: #e8eaed; }
QComboBox QAbstractItemView { 
    background-color: #2d2e30; 
    color: #e8eaed; 
    border: 1px solid #5f6368; 
    selection-background-color: #3c4043; 
    selection-color: #8ab4f8; 
    outline: none;
    padding: 0px;
    margin: 0px;
}
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left: 1px solid #5f6368; border-top-right-radius: 6px; border-bottom-right-radius: 6px; background-color: #35363a; }
QComboBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #9aa0a6; width: 0; height: 0; }
QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus { border: 2px solid #8ab4f8; }
QTabWidget::pane { border: 1px solid #3c4043; background: #2d2e30; }
QTabBar::tab:selected { color: #8ab4f8; border-bottom: 2px solid #8ab4f8; }
QMessageBox { background-color: #2d2e30; }
QMessageBox QLabel { color: #e8eaed; font-size: 14px; }
QMessageBox QPushButton { min-width: 80px; }
QInputDialog { background-color: #2d2e30; }
QInputDialog QLabel { color: #e8eaed; font-size: 14px; }
QInputDialog QSpinBox { background-color: #3c4043; border: 1px solid #5f6368; color: #e8eaed; border-radius: 6px; padding: 8px 12px; }
QInputDialog QPushButton { min-width: 80px; }
QColorDialog { background-color: #2d2e30; color: #e8eaed; }
QColorDialog QLabel { color: #e8eaed; }
QColorDialog QFrame { background-color: #2d2e30; }
QColorDialog QLineEdit, QColorDialog QSpinBox { background-color: #3c4043; border: 1px solid #5f6368; color: #e8eaed; border-radius: 6px; padding: 6px 10px; }
QColorDialog QPushButton { min-width: 80px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px 4px 2px; }
QScrollBar::handle:vertical { background: #5f6368; border-radius: 4px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: #80868b; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: transparent; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px 4px 2px 4px; }
QScrollBar::handle:horizontal { background: #5f6368; border-radius: 4px; min-width: 32px; }
QScrollBar::handle:horizontal:hover { background: #80868b; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: transparent; border: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
"""


class UpdateCheckWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.finished.emit(check_for_update(APP_VERSION))
        except Exception as error:
            self.failed.emit(str(error))


class UpdateInstallWorker(QObject):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, update_info):
        super().__init__()
        self.update_info = update_info

    def run(self):
        try:
            install_update(self.update_info, self.progress.emit)
            self.finished.emit()
        except Exception as error:
            self.failed.emit(str(error))


class HouseholdSelector(QWidget):
    def __init__(self, on_selected):
        super().__init__()
        self.on_selected = on_selected
        self.setWindowTitle("가계부 선택")
        self.setWindowIcon(QIcon(APP_ICON_PATH))
        self.resize(700, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        title = QLabel("🏠 관리할 가계부를 선택하세요")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a73e8;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget { border: 1px solid #dadce0; border-radius: 12px; background: white; padding: 10px; } QListWidget::item { height: 60px; font-size: 15px; border-bottom: 1px solid #f1f3f4; padding-left: 10px; } QListWidget::item:selected { background-color: #e8f0fe; color: #1a73e8; border-radius: 8px; }")
        self.list_widget.itemDoubleClicked.connect(self.handle_select)
        layout.addWidget(self.list_widget)
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("+ 새 가계부 만들기"); self.create_btn.clicked.connect(self.handle_create)
        self.rename_btn = QPushButton("🏷️ 이름 변경"); self.rename_btn.clicked.connect(self.handle_rename)
        self.delete_btn = QPushButton("🗑️ 삭제"); self.delete_btn.setObjectName("DeleteBtn"); self.delete_btn.clicked.connect(self.handle_delete)
        btn_layout.addWidget(self.create_btn); btn_layout.addWidget(self.rename_btn); btn_layout.addWidget(self.delete_btn); layout.addLayout(btn_layout)
        self.select_btn = QPushButton("선택 완료 (더블클릭 가능)"); self.select_btn.setFixedHeight(50); self.select_btn.setStyleSheet("font-size: 16px; font-weight: bold;"); self.select_btn.clicked.connect(self.handle_select); layout.addWidget(self.select_btn)
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #9aa0a6; font-size: 12px; font-weight: 500;")
        layout.addWidget(version_label)
        self.refresh_list()


    def refresh_list(self):
        self.list_widget.clear()
        for hid, name, date in get_households():
            item = QListWidgetItem(f"{name} (생성일: {date[:10]})")
            item.setData(Qt.ItemDataRole.UserRole, hid); self.list_widget.addItem(item)

    def handle_create(self):
        name, ok = QInputDialog.getText(self, "새 가계부", "가계부 이름을 입력하세요:")
        if ok and name.strip():
            if add_household(name.strip()): self.refresh_list()
            else: QMessageBox.warning(self, "오류", "이미 존재하는 이름입니다.")

    def handle_rename(self):
        item = self.list_widget.currentItem()
        if not item: return
        hid = item.data(Qt.ItemDataRole.UserRole); old_name = item.text().split(' (')[0]
        new_name, ok = QInputDialog.getText(self, "가계부 이름 변경", f"'{old_name}'의 새로운 이름을 입력하세요:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            if update_household_name(hid, new_name.strip()): self.refresh_list()
            else: QMessageBox.warning(self, "오류", "이미 존재하는 이름이거나 오류가 발생했습니다.")

    def handle_delete(self):
        item = self.list_widget.currentItem()
        if not item: return
        hid = item.data(Qt.ItemDataRole.UserRole); name = item.text()
        reply = QMessageBox.question(self, "삭제 확인", f"'{name}'의 모든 데이터를 영구 삭제하시겠습니까?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes: delete_household(hid); self.refresh_list()

    def handle_select(self):
        item = self.list_widget.currentItem()
        if item: self.on_selected(item.data(Qt.ItemDataRole.UserRole), item.text().split(' (')[0])
        else: QMessageBox.warning(self, "안내", "가계부를 먼저 선택해 주세요.")

class AppWindow(QMainWindow):
    def __init__(self, hid, hname, on_back):
        super().__init__()
        self.hid = hid; self.hname = hname; self.on_back = on_back
        self.setWindowTitle(f"Household Manager - {hname}"); self.resize(2000, 900); self.is_dark_mode = False
        self.setWindowIcon(QIcon(APP_ICON_PATH))
        self.is_loading = True
        self.spinner_index = 0
        main_layout = QHBoxLayout(); main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        central_widget = QWidget(); central_widget.setLayout(main_layout); self.setCentralWidget(central_widget)

        sidebar_container = QWidget(); sidebar_container.setFixedWidth(240); sidebar_layout = QVBoxLayout(sidebar_container); sidebar_layout.setContentsMargins(0, 10, 0, 10); sidebar_layout.setSpacing(5)
        btn_row = QHBoxLayout(); btn_row.setContentsMargins(10, 0, 10, 0)
        self.theme_btn = QPushButton("🌙 테마"); self.theme_btn.setFlat(True); self.theme_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px;")
        self.theme_btn.clicked.connect(self.toggle_theme)
        btn_row.addWidget(self.theme_btn); sidebar_layout.addLayout(btn_row)

        excel_btn_row = QHBoxLayout(); excel_btn_row.setContentsMargins(10, 0, 10, 0)
        self.import_btn = QPushButton("📂 엑셀 임포트"); self.import_btn.setFlat(True); self.import_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px;")
        self.import_btn.clicked.connect(self.handle_excel_import)
        self.export_btn = QPushButton("📤 엑셀 내보내기"); self.export_btn.setFlat(True); self.export_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px;")
        self.export_btn.clicked.connect(self.handle_excel_export)
        excel_btn_row.addWidget(self.import_btn); excel_btn_row.addWidget(self.export_btn); sidebar_layout.addLayout(excel_btn_row)

        back_btn_row = QHBoxLayout(); back_btn_row.setContentsMargins(10, 0, 10, 0)
        self.back_btn = QPushButton("⬅️ 가계부 선택 이동"); self.back_btn.setFlat(True); self.back_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px; margin-top: 5px;"); self.back_btn.clicked.connect(self.on_back)
        back_btn_row.addWidget(self.back_btn); sidebar_layout.addLayout(back_btn_row)

        self.sidebar = QListWidget(); sidebar_layout.addWidget(self.sidebar); main_layout.addWidget(sidebar_container)
        sidebar_layout.addStretch()
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setStyleSheet("color: #9aa0a6; font-size: 12px; font-weight: 500; padding: 6px 0;")
        sidebar_layout.addWidget(self.version_label)

        content_container = QVBoxLayout(); content_container.setContentsMargins(30, 20, 30, 20); self.content_stack = QStackedWidget(); content_container.addWidget(self.content_stack); main_layout.addLayout(content_container)

        self.create_loading_page()
        self.set_loading_controls_enabled(False)
        QTimer.singleShot(0, self.start_page_loading)

    def create_loading_page(self):
        self.loading_page = QFrame()
        self.loading_page.setObjectName("MainLoadingPage")
        self.loading_page.setStyleSheet("""
            QFrame#MainLoadingPage {
                background-color: #f8f9fa;
                border: 1px solid #dadce0;
                border-radius: 12px;
            }
            QLabel#MainLoadingSpinner {
                color: #1a73e8;
                font-size: 38px;
                font-weight: 700;
                background: transparent;
            }
            QLabel#MainLoadingTitle {
                color: #202124;
                font-size: 18px;
                font-weight: 700;
                background: transparent;
            }
            QLabel#MainLoadingMessage {
                color: #5f6368;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
            }
        """)
        loading_layout = QVBoxLayout(self.loading_page)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.setSpacing(12)
        self.loading_spinner = QLabel("⠋")
        self.loading_spinner.setObjectName("MainLoadingSpinner")
        self.loading_spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_title = QLabel("가계부를 불러오는 중입니다")
        loading_title.setObjectName("MainLoadingTitle")
        loading_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_message = QLabel("데이터를 준비하고 있습니다...")
        self.loading_message.setObjectName("MainLoadingMessage")
        self.loading_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(self.loading_spinner)
        loading_layout.addWidget(loading_title)
        loading_layout.addWidget(self.loading_message)
        self.content_stack.addWidget(self.loading_page)
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.update_loading_spinner)
        self.loading_timer.start(90)

    def update_loading_spinner(self):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = (self.spinner_index + 1) % len(frames)
        self.loading_spinner.setText(frames[self.spinner_index])

    def set_loading_controls_enabled(self, enabled):
        self.sidebar.setEnabled(enabled)
        self.theme_btn.setEnabled(enabled)
        self.import_btn.setEnabled(enabled)
        self.export_btn.setEnabled(enabled)
        self.back_btn.setEnabled(enabled)

    def start_page_loading(self):
        self.pages = {}
        self.month_pages = {}
        self.loading_steps = [
            ("설정 정보를 불러오는 중입니다...", lambda: self.add_named_page("settings", SettingsTab(hid=self.hid))),
            ("예산 정보를 불러오는 중입니다...", lambda: self.add_named_page("budget", BudgetTab(hid=self.hid))),
            ("자산 정보를 불러오는 중입니다...", lambda: self.add_named_page("asset", AssetTab(hid=self.hid))),
            ("월별 리포트를 불러오는 중입니다...", lambda: self.add_named_page("report_monthly", MonthlyReportTab(hid=self.hid))),
            ("연도별 리포트를 불러오는 중입니다...", lambda: self.add_named_page("report_yearly", YearlyReportTab(hid=self.hid))),
        ]
        for month in range(1, 13):
            self.loading_steps.append(
                (f"{month}월 가계부를 불러오는 중입니다...", lambda m=month: self.add_month_page(m))
            )
        self.loading_step_index = 0
        self.load_next_page_step()

    def add_named_page(self, key, widget):
        self.pages[key] = widget
        self.content_stack.addWidget(widget)

    def add_month_page(self, month):
        widget = LedgerTab(hid=self.hid, month=month)
        self.month_pages[month] = widget
        self.content_stack.addWidget(widget)

    def load_next_page_step(self):
        if self.loading_step_index >= len(self.loading_steps):
            self.finish_page_loading()
            return
        message, _ = self.loading_steps[self.loading_step_index]
        self.loading_message.setText(message)
        QTimer.singleShot(10, self.run_current_page_step)

    def run_current_page_step(self):
        _, loader = self.loading_steps[self.loading_step_index]
        loader()
        self.loading_step_index += 1
        QTimer.singleShot(10, self.load_next_page_step)

    def finish_page_loading(self):
        self.loading_timer.stop()
        self.content_stack.removeWidget(self.loading_page)
        self.loading_page.deleteLater()
        self.is_loading = False
        self.setup_sidebar()
        self.sidebar.currentRowChanged.connect(self.handle_navigation)
        self.set_loading_controls_enabled(True)
        self.sidebar.setCurrentRow(0)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        QApplication.instance().setStyleSheet(DARK_STYLE if self.is_dark_mode else LIGHT_STYLE)
        self.theme_btn.setText("☀️ 테마" if self.is_dark_mode else "🌙 테마")
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'load_data'): current_widget.load_data()
        if hasattr(current_widget, 'refresh_data'): current_widget.refresh_data()

    def handle_excel_import(self):
        from PyQt6.QtWidgets import QFileDialog; from ui.migration_util import import_from_excel
        file_path, _ = QFileDialog.getOpenFileName(self, "엑셀 가져오기", "", "Excel Files (*.xlsx *.xls)")
        if file_path and import_from_excel(self.hid, file_path, self):
            for i in range(self.content_stack.count()):
                w = self.content_stack.widget(i)
                if hasattr(w, 'load_data'): w.load_data()
                if hasattr(w, 'refresh_data'): w.refresh_data()

    def handle_excel_export(self):
        from datetime import datetime
        from PyQt6.QtWidgets import QFileDialog
        from ui.migration_util import export_to_excel

        year, ok = QInputDialog.getInt(
            self, "엑셀 내보내기", "내보낼 연도를 입력하세요:",
            datetime.now().year, 1900, 2100, 1
        )
        if not ok:
            return

        default_name = f"{self.hname}_{year}_가계부.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "엑셀 내보내기", default_name, "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".xlsx"):
            file_path += ".xlsx"
        export_to_excel(self.hid, year, file_path, self)

    def setup_pages(self):
        self.pages = {
            'settings': SettingsTab(hid=self.hid), 
            'budget': BudgetTab(hid=self.hid), 
            'asset': AssetTab(hid=self.hid),
            'report_monthly': MonthlyReportTab(hid=self.hid),
            'report_yearly': YearlyReportTab(hid=self.hid)
        }
        self.month_pages = {m: LedgerTab(hid=self.hid, month=m) for m in range(1, 13)}
        self.content_stack.addWidget(self.pages['settings'])       # 0
        self.content_stack.addWidget(self.pages['budget'])         # 1
        self.content_stack.addWidget(self.pages['asset'])          # 2
        self.content_stack.addWidget(self.pages['report_monthly']) # 3
        self.content_stack.addWidget(self.pages['report_yearly'])  # 4
        for m in range(1, 13): self.content_stack.addWidget(self.month_pages[m]) # 5-16

    def setup_sidebar(self):
        self.sidebar.clear()
        self.sidebar.addItem(QListWidgetItem("⚙️  설정"))           # 0
        self.sidebar.addItem(QListWidgetItem("📊  예산 설정"))       # 1
        self.sidebar.addItem(QListWidgetItem("💰  자산 설정"))       # 2
        self.sidebar.addItem(QListWidgetItem("📈  월별 리포트"))     # 3
        self.sidebar.addItem(QListWidgetItem("📅  연도별 리포트"))   # 4
        h = QListWidgetItem("📋  월별 가계부"); h.setFlags(Qt.ItemFlag.NoItemFlags); self.sidebar.addItem(h) # 5
        for i in range(1, 13): self.sidebar.addItem(QListWidgetItem(f"      {i}월")) # 6-17

    def handle_navigation(self, row):
        if self.is_loading:
            return
        idx = -1
        if 0 <= row <= 4: idx = row
        elif 6 <= row <= 17: idx = 5 + (row - 6)
        if idx != -1:
            self.content_stack.setCurrentIndex(idx)
            w = self.content_stack.currentWidget()
            if hasattr(w, 'load_data'): w.load_data()
            if hasattr(w, 'refresh_data'): w.refresh_data()

class MainController:
    def __init__(self):
        self.selector = None; self.app_window = None
        self.update_thread = None
        self.update_worker = None
        self.update_dialog = None

    def show_selector(self):
        if self.app_window: self.app_window.close()
        self.selector = HouseholdSelector(self.start_app); self.selector.show()
        QTimer.singleShot(1200, self.check_for_updates)

    def start_app(self, hid, hname):
        self.selector.close(); self.app_window = AppWindow(hid, hname, self.show_selector); self.app_window.showMaximized()

    def active_window(self):
        return self.app_window or self.selector

    def check_for_updates(self):
        if not getattr(sys, "frozen", False) or self.update_thread:
            return
        self.update_thread = QThread()
        self.update_worker = UpdateCheckWorker()
        self.update_worker.moveToThread(self.update_thread)
        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.finished.connect(self.handle_update_check_finished)
        self.update_worker.failed.connect(self.handle_update_check_failed)
        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.failed.connect(self.update_thread.quit)
        self.update_worker.finished.connect(self.update_worker.deleteLater)
        self.update_worker.failed.connect(self.update_worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)
        self.update_thread.finished.connect(self.clear_update_thread)
        self.update_thread.start()

    def handle_update_check_finished(self, update_info):
        if not update_info:
            return
        QTimer.singleShot(0, lambda: self.prompt_update_available(update_info))

    def prompt_update_available(self, update_info):
        reply = QMessageBox.question(
            self.active_window(),
            "업데이트 확인",
            f"새 버전 {update_info.tag_name}이 있습니다.\n"
            f"현재 버전: v{APP_VERSION}\n\n"
            "지금 자동 업데이트할까요?\n"
            "업데이트가 완료되면 프로그램이 자동으로 재시작됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.start_update_install(update_info)

    def handle_update_check_failed(self, message):
        print(f"Update check failed: {message}")

    def start_update_install(self, update_info):
        if self.update_thread:
            QTimer.singleShot(100, lambda: self.start_update_install(update_info))
            return
        self.update_dialog = QDialog(self.active_window())
        self.update_dialog.setWindowTitle("업데이트")
        self.update_dialog.setModal(True)
        self.update_dialog.setFixedWidth(420)
        update_layout = QVBoxLayout(self.update_dialog)
        update_layout.setContentsMargins(24, 22, 24, 22)
        update_layout.setSpacing(12)
        self.update_status_label = QLabel("업데이트를 준비하고 있습니다.")
        self.update_status_label.setWordWrap(True)
        self.update_progress_bar = QProgressBar()
        self.update_progress_bar.setRange(0, 100)
        self.update_progress_bar.setValue(0)
        update_layout.addWidget(self.update_status_label)
        update_layout.addWidget(self.update_progress_bar)
        self.update_dialog.show()

        self.update_thread = QThread()
        self.update_worker = UpdateInstallWorker(update_info)
        self.update_worker.moveToThread(self.update_thread)
        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.progress.connect(self.handle_update_install_progress)
        self.update_worker.finished.connect(self.handle_update_install_finished)
        self.update_worker.failed.connect(self.handle_update_install_failed)
        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.failed.connect(self.update_thread.quit)
        self.update_worker.finished.connect(self.update_worker.deleteLater)
        self.update_worker.failed.connect(self.update_worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)
        self.update_thread.finished.connect(self.clear_update_thread)
        self.update_thread.start()

    def handle_update_install_progress(self, message, percent):
        if hasattr(self, "update_status_label"):
            self.update_status_label.setText(message)
        if hasattr(self, "update_progress_bar"):
            self.update_progress_bar.setValue(max(0, min(100, percent)))

    def handle_update_install_finished(self):
        if self.update_dialog:
            self.update_dialog.close()
        QApplication.quit()

    def handle_update_install_failed(self, message):
        if self.update_dialog:
            self.update_dialog.close()
        QMessageBox.critical(
            self.active_window(),
            "업데이트 실패",
            f"자동 업데이트에 실패했습니다.\n{message}",
        )

    def clear_update_thread(self):
        self.update_thread = None
        self.update_worker = None

def main():
    init_db(); app = QApplication(sys.argv); app.setWindowIcon(QIcon(APP_ICON_PATH)); app.setStyleSheet(LIGHT_STYLE); controller = MainController(); controller.show_selector(); sys.exit(app.exec())

if __name__ == "__main__":
    main()
