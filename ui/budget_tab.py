from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QMessageBox, 
                             QHeaderView, QSpinBox)
from PyQt6.QtCore import Qt
from database import get_categories, get_budgets, save_budget

class BudgetTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()

        # 1. Year Selection
        top_layout = QHBoxLayout()
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(2026)
        self.year_spin.valueChanged.connect(self.load_data)
        
        save_btn = QPushButton("전체 예산 저장")
        save_btn.clicked.connect(self.handle_save)

        top_layout.addWidget(QLabel("연도:"))
        top_layout.addWidget(self.year_spin)
        top_layout.addStretch()
        top_layout.addWidget(save_btn)
        layout.addLayout(top_layout)

        # 2. Budget Table (Row: Categories, Col: Month 1-12)
        self.table = QTableWidget()
        headers = ["카테고리"] + [f"{i}월" for i in range(1, 13)]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_data(self):
        year = self.year_spin.value()
        # Only budget for "소비" (Expense)
        categories = get_categories("소비")
        budgets = get_budgets(year) # List of (id, month, cat_id, amount, parent, sub)
        
        budget_map = {} # (cat_id, month) -> amount
        for b in budgets:
            budget_map[(b[2], b[1])] = b[3]

        self.table.setRowCount(0)
        for cat in categories:
            cat_id = cat[0]
            cat_name = f"{cat[2]} > {cat[3]}"
            
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            
            # Col 0: Category Name
            item = QTableWidgetItem(cat_name)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Non-editable
            item.setData(Qt.ItemDataRole.UserRole, cat_id)
            self.table.setItem(row_idx, 0, item)
            
            # Cols 1-12: Months
            for month in range(1, 13):
                amount = budget_map.get((cat_id, month), 0)
                self.table.setItem(row_idx, month, QTableWidgetItem(str(amount)))

    def handle_save(self):
        year = self.year_spin.value()
        row_count = self.table.rowCount()
        
        try:
            for row in range(row_count):
                cat_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                for month in range(1, 13):
                    amount_str = self.table.item(row, month).text().strip()
                    amount = int(amount_str) if amount_str else 0
                    save_budget(year, month, cat_id, amount)
            
            QMessageBox.information(self, "완료", f"{year}년 예산이 저장되었습니다.")
        except ValueError:
            QMessageBox.warning(self, "오류", "예산 금액은 숫자만 입력 가능합니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 중 오류 발생: {e}")
