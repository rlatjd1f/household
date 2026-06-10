from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QMessageBox, 
                             QHeaderView, QSpinBox, QStyledItemDelegate, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIntValidator
from database import get_detailed_budgets, save_detailed_budget

class NumericDelegate(QStyledItemDelegate):
    """Delegate that only allows numeric input in the editor."""
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        # Allow only positive integers
        validator = QIntValidator(0, 999999999, editor)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor, index):
        # Clean commas when entering edit mode
        text = index.data(Qt.ItemDataRole.DisplayRole).replace(',', '')
        editor.setText(text)

class BudgetTab(QWidget):
    def __init__(self):
        super().__init__()
        self.categories = [
            "🏠 고정지출(주거)", "💰 이자", "🏘️ 월세", "🍔 식비", 
            "🚌 자동차·교통", "💇 개인관리", "🎬 문화생활", "🛍️ 쇼핑", 
            "📈 변동지출", "🚀 투자", "📉 상환"
        ]
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        top_layout = QHBoxLayout()
        header_title = QLabel("📊 항목별 월간 예산 설정")
        header_title.setStyleSheet("font-weight: bold; font-size: 18px; color: #1a73e8;")
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(2026)
        self.year_spin.setFixedWidth(100)
        self.year_spin.valueChanged.connect(self.load_data)
        
        save_btn = QPushButton("전체 저장")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.handle_save)

        top_layout.addWidget(header_title)
        top_layout.addStretch()
        top_layout.addWidget(QLabel("연도:"))
        top_layout.addWidget(self.year_spin)
        top_layout.addWidget(save_btn)
        layout.addLayout(top_layout)

        # Budget Table
        self.table = QTableWidget(len(self.categories) + 1, 13)
        headers = ["항목"] + [f"{i}월" for i in range(1, 13)]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for i in range(1, 13):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(45)
        
        # Apply Numeric Delegate to all month columns (1-12)
        delegate = NumericDelegate(self)
        for i in range(1, 13):
            self.table.setItemDelegateForColumn(i, delegate)
        
        for i, cat in enumerate(self.categories):
            item = QTableWidgetItem(cat)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, item)
            for m in range(1, 13):
                cell = QTableWidgetItem("0")
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, m, cell)

        # Total Row
        total_row = len(self.categories)
        total_item = QTableWidgetItem("✨ 월별 총합")
        total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        total_item.setBackground(QColor("#f1f3f4") if not self.is_dark() else QColor("#3c4043"))
        self.table.setItem(total_row, 0, total_item)
        for m in range(1, 13):
            t_cell = QTableWidgetItem("0")
            t_cell.setFlags(t_cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            t_cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(total_row, m, t_cell)

        self.table.itemChanged.connect(self.handle_item_changed)
        layout.addWidget(self.table)

    def is_dark(self):
        from PyQt6.QtWidgets import QApplication
        return "background-color: #202124" in (QApplication.instance().styleSheet() or "")

    def format_num(self, val):
        try:
            if isinstance(val, str):
                val = val.replace(',', '').strip()
                val = int(val) if val else 0
            return f"{val:,}"
        except:
            return "0"

    def handle_item_changed(self, item):
        col = item.column()
        if col == 0: return 
        if item.row() == len(self.categories): return
        
        # Auto-format commas when editing is done
        self.table.blockSignals(True)
        text = item.text().replace(',', '')
        if text.isdigit():
            item.setText(self.format_num(int(text)))
        else:
            item.setText("0")
        self.table.blockSignals(False)

        self.update_month_total(col)

    def update_month_total(self, col):
        self.table.blockSignals(True)
        total = 0
        for row in range(len(self.categories)):
            item = self.table.item(row, col)
            if item:
                val_str = item.text().replace(',', '').strip()
                try: total += int(val_str)
                except: pass
        
        total_item = self.table.item(len(self.categories), col)
        total_item.setText(self.format_num(total))
        total_item.setForeground(QColor("#1a73e8") if not self.is_dark() else QColor("#8ab4f8"))
        self.table.blockSignals(False)

    def load_data(self):
        year = self.year_spin.value()
        data = get_detailed_budgets(year) 
        
        self.table.blockSignals(True)
        for row, cat in enumerate(self.categories):
            cat_clean = cat.split(' ')[1] 
            cat_data = data.get(cat_clean, {})
            for month in range(1, 13):
                amt = cat_data.get(month, 0)
                self.table.item(row, month).setText(self.format_num(amt))
        
        for m in range(1, 13):
            self.update_month_total(m)
        self.table.blockSignals(False)

    def handle_save(self):
        year = self.year_spin.value()
        try:
            for row, cat in enumerate(self.categories):
                cat_clean = cat.split(' ')[1]
                for month in range(1, 13):
                    item = self.table.item(row, month)
                    amt_str = item.text().replace(',', '').strip()
                    amt = int(amt_str) if amt_str else 0
                    save_detailed_budget(year, month, cat_clean, amt)
            
            QMessageBox.information(self, "완료", f"{year}년 항목별 예산이 저장되었습니다.")
            self.load_data()
        except ValueError:
            QMessageBox.warning(self, "오류", "금액은 숫자만 입력 가능합니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 중 오류 발생: {e}")
