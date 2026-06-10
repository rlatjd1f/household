from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QMessageBox, 
                             QHeaderView, QFrame)
from PyQt6.QtCore import Qt
from database import (get_ledger_entries, add_ledger_entry, update_ledger_entry, 
                      delete_ledger_entry, get_categories, get_assets)

class LedgerSpreadsheet(QTableWidget):
    """A reusable spreadsheet-style table for Income or Expense."""
    def __init__(self, ledger_tab, entry_type):
        super().__init__(0, 8)
        self.ledger_tab = ledger_tab
        self.entry_type = entry_type # "수입" or "지출"
        self.init_ui()

    def init_ui(self):
        self.setHorizontalHeaderLabels(["ID", "날짜", "대분류", "중분류", "자산", "금액", "메모", ""])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setColumnHidden(0, True) # Hide ID
        self.setColumnHidden(7, True) # Placeholder for alignment
        self.itemChanged.connect(self.handle_item_changed)

    def handle_item_changed(self, item):
        row = item.row()
        id_item = self.item(row, 0)
        entry_id = int(id_item.text()) if id_item and id_item.text() else None
        
        try:
            date = self.item(row, 1).text() if self.item(row, 1) else ""
            parent = self.item(row, 2).text() if self.item(row, 2) else ""
            sub = self.item(row, 3).text() if self.item(row, 3) else ""
            asset_name = self.item(row, 4).text() if self.item(row, 4) else ""
            amount_str = self.item(row, 5).text() if self.item(row, 5) else "0"
            amount = int(amount_str.replace(',', ''))
            memo = self.item(row, 6).text() if self.item(row, 6) else ""
            
            cat_id = self.ledger_tab.resolve_category_id(self.entry_type, parent, sub)
            asset_id = self.ledger_tab.resolve_asset_id(asset_name)
            
            if not cat_id or not asset_id: return

            if entry_id:
                update_ledger_entry(entry_id, date, self.entry_type, cat_id, asset_id, amount, memo)
            else:
                new_id = add_ledger_entry(date, self.entry_type, cat_id, asset_id, amount, memo, "")
                if new_id:
                    self.blockSignals(True)
                    self.setItem(row, 0, QTableWidgetItem(str(new_id)))
                    self.blockSignals(False)
            
            self.ledger_tab.refresh_summary()
        except Exception as e:
            print(f"Spreadsheet error ({self.entry_type}): {e}")

class LedgerTab(QWidget):
    def __init__(self, month):
        super().__init__()
        self.month = month
        self.year = 2026
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Summary Header
        self.summary_label = QLabel("수입: 0 | 지출: 0 | 잔액: 0")
        self.summary_label.setObjectName("SummaryLabel")
        layout.addWidget(self.summary_label)

        # Container for side-by-side or stacked tables
        content_layout = QHBoxLayout()
        
        # 1. Income Area
        income_box = QFrame()
        income_box.setObjectName("ContentCard")
        income_vbox = QVBoxLayout(income_box)
        income_title = QLabel("💰 수입 내역")
        income_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #1a73e8;")
        
        self.income_table = LedgerSpreadsheet(self, "수입")
        
        income_btns = QHBoxLayout()
        add_inc = QPushButton("+ 수입 행 추가")
        add_inc.clicked.connect(lambda: self.add_row(self.income_table))
        del_inc = QPushButton("- 삭제")
        del_inc.setObjectName("DeleteBtn")
        del_inc.clicked.connect(lambda: self.delete_row(self.income_table))
        income_btns.addWidget(add_inc)
        income_btns.addWidget(del_inc)
        income_btns.addStretch()
        
        income_vbox.addWidget(income_title)
        income_vbox.addWidget(self.income_table)
        income_vbox.addLayout(income_btns)
        
        # 2. Expense Area
        expense_box = QFrame()
        expense_box.setObjectName("ContentCard")
        expense_vbox = QVBoxLayout(expense_box)
        expense_title = QLabel("💸 지출 내역")
        expense_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #d93025;")
        
        self.expense_table = LedgerSpreadsheet(self, "지출")
        
        expense_btns = QHBoxLayout()
        add_exp = QPushButton("+ 지출 행 추가")
        add_exp.clicked.connect(lambda: self.add_row(self.expense_table))
        del_exp = QPushButton("- 삭제")
        del_exp.setObjectName("DeleteBtn")
        del_exp.clicked.connect(lambda: self.delete_row(self.expense_table))
        expense_btns.addWidget(add_exp)
        expense_btns.addWidget(del_exp)
        expense_btns.addStretch()
        
        expense_vbox.addWidget(expense_title)
        expense_vbox.addWidget(self.expense_table)
        expense_vbox.addLayout(expense_btns)

        content_layout.addWidget(income_box)
        content_layout.addWidget(expense_box)
        layout.addLayout(content_layout)

    def refresh_data(self):
        self.income_table.blockSignals(True)
        self.expense_table.blockSignals(True)
        
        entries = get_ledger_entries(self.year, self.month)
        self.income_table.setRowCount(0)
        self.expense_table.setRowCount(0)
        
        for e in entries:
            table = self.income_table if e[2] == "수입" else self.expense_table
            row = table.rowCount()
            table.insertRow(row)
            # id, date, parent, sub, asset, amount, memo
            table.setItem(row, 0, QTableWidgetItem(str(e[0])))
            table.setItem(row, 1, QTableWidgetItem(e[1]))
            table.setItem(row, 2, QTableWidgetItem(e[7]))
            table.setItem(row, 3, QTableWidgetItem(e[8]))
            table.setItem(row, 4, QTableWidgetItem(e[9]))
            table.setItem(row, 5, QTableWidgetItem(str(e[5])))
            table.setItem(row, 6, QTableWidgetItem(e[6]))

        self.income_table.blockSignals(False)
        self.expense_table.blockSignals(False)
        self.refresh_summary()

    def add_row(self, table):
        table.blockSignals(True)
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 1, QTableWidgetItem(f"{self.year}-{self.month:02d}-01"))
        table.setItem(row, 5, QTableWidgetItem("0"))
        table.scrollToBottom()
        table.blockSignals(False)

    def delete_row(self, table):
        row = table.currentRow()
        if row < 0: return
        id_item = table.item(row, 0)
        if id_item and id_item.text():
            delete_ledger_entry(int(id_item.text()))
        table.removeRow(row)
        self.refresh_summary()

    def refresh_summary(self):
        def sum_table(table):
            total = 0
            for r in range(table.rowCount()):
                item = table.item(r, 5)
                if item:
                    try: total += int(item.text().replace(',', ''))
                    except: pass
            return total
        
        inc = sum_table(self.income_table)
        exp = sum_table(self.expense_table)
        self.summary_label.setText(f"수입: {inc:,} | 지출: {exp:,} | 잔액: {inc - exp:,}")

    def resolve_category_id(self, etype, parent, sub):
        db_type = "소비" if etype == "지출" else "소득"
        from database import get_categories
        categories = get_categories(db_type)
        for c in categories:
            if c[2] == parent and c[3] == sub: return c[0]
        return None

    def resolve_asset_id(self, name):
        from database import get_assets
        assets = get_assets()
        for a in assets:
            if a[1] == name: return a[0]
        return None
