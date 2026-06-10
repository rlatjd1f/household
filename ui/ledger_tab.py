from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QMessageBox, 
                             QHeaderView, QFrame)
from PyQt6.QtCore import Qt
from database import (get_ledger_entries, add_ledger_entry, update_ledger_entry, 
                      delete_ledger_entry, get_categories, get_assets)

class LedgerSpreadsheet(QTableWidget):
    """A highly customized spreadsheet table to match the user's layout."""
    def __init__(self, ledger_tab, entry_type, columns):
        super().__init__(0, len(columns) + 1) # +1 for hidden ID
        self.ledger_tab = ledger_tab
        self.entry_type = entry_type
        self.col_names = columns
        self.init_ui()

    def init_ui(self):
        headers = ["ID"] + self.col_names
        self.setHorizontalHeaderLabels(headers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setColumnHidden(0, True) # Hide ID
        self.itemChanged.connect(self.handle_item_changed)

    def handle_item_changed(self, item):
        row = item.row()
        id_item = self.item(row, 0)
        entry_id = int(id_item.text()) if id_item and id_item.text() else None
        
        try:
            # Map columns based on entry_type
            if self.entry_type == "지출":
                # [소비날짜, 결제수단, 수단명, 대분류, 항목, 지출금액, 사용처, 코멘트]
                date = self.get_text(row, 1)
                pay_method = self.get_text(row, 2)
                asset_name = self.get_text(row, 3)
                parent = self.get_text(row, 4)
                sub = self.get_text(row, 5)
                amount = self.get_int(row, 6)
                payee = self.get_text(row, 7)
                memo = self.get_text(row, 8)
            else:
                # [소득날짜, 대분류, 항목, 소득 금액, 소득처]
                date = self.get_text(row, 1)
                parent = self.get_text(row, 2)
                sub = self.get_text(row, 3)
                amount = self.get_int(row, 4)
                payee = self.get_text(row, 5)
                pay_method = ""
                asset_name = ""
                memo = ""

            cat_id = self.ledger_tab.resolve_category_id(self.entry_type, parent, sub)
            asset_id = self.ledger_tab.resolve_asset_id(asset_name) if asset_name else None
            
            # For Income, if asset is not provided, we might need a default or allow NULL
            # But based on DB, asset_id can be NULL if it's not a transfer
            
            if entry_id:
                update_ledger_entry(entry_id, date, self.entry_type, cat_id, asset_id, amount, memo, payee, pay_method)
            else:
                # Add only if essential fields are present
                if date and (cat_id or payee):
                    new_id = add_ledger_entry(date, self.entry_type, cat_id, asset_id, amount, memo, payee, pay_method)
                    if new_id:
                        self.blockSignals(True)
                        self.setItem(row, 0, QTableWidgetItem(str(new_id)))
                        self.blockSignals(False)
            
            self.ledger_tab.refresh_summary()
        except Exception as e:
            print(f"Spreadsheet error ({self.entry_type}): {e}")

    def get_text(self, row, col):
        item = self.item(row, col)
        return item.text().strip() if item else ""

    def get_int(self, row, col):
        text = self.get_text(row, col).replace(',', '')
        try: return int(text)
        except: return 0

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
        layout.setSpacing(15)

        # Summary Header
        self.summary_label = QLabel("수입: 0 | 지출: 0 | 잔액: 0")
        self.summary_label.setObjectName("SummaryLabel")
        layout.addWidget(self.summary_label)

        content_layout = QHBoxLayout()
        
        # 1. Consumption (Expense) Area - 8 Columns
        exp_columns = ["소비날짜", "결제수단", "수단명", "대분류", "항목", "지출금액", "사용처", "코멘트"]
        self.expense_box = self.create_section("💸 소비 내역 (지출)", "지출", exp_columns)
        
        # 2. Income Area - 5 Columns
        inc_columns = ["소득날짜", "대분류", "항목", "소득 금액", "소득처"]
        self.income_box = self.create_section("💰 소득 내역 (수입)", "수입", inc_columns)

        content_layout.addWidget(self.expense_box, 3) # More weight to expense
        content_layout.addWidget(self.income_box, 2)
        layout.addLayout(content_layout)

    def create_section(self, title, etype, columns):
        box = QFrame()
        box.setObjectName("ContentCard")
        vbox = QVBoxLayout(box)
        
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {'#d93025' if etype=='지출' else '#1a73e8'};")
        
        table = LedgerSpreadsheet(self, etype, columns)
        if etype == "지출": self.expense_table = table
        else: self.income_table = table
        
        btns = QHBoxLayout()
        add_btn = QPushButton(f"+ {etype} 행 추가")
        add_btn.clicked.connect(lambda: self.add_row(table))
        del_btn = QPushButton("- 삭제")
        del_btn.setObjectName("DeleteBtn")
        del_btn.clicked.connect(lambda: self.delete_row(table))
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addStretch()
        
        vbox.addWidget(lbl)
        vbox.addWidget(table)
        vbox.addLayout(btns)
        return box

    def refresh_data(self):
        self.income_table.blockSignals(True)
        self.expense_table.blockSignals(True)
        
        entries = get_ledger_entries(self.year, self.month)
        self.income_table.setRowCount(0)
        self.expense_table.setRowCount(0)
        
        for e in entries:
            # (id, date, type, cat_id, asset_id, amount, memo, payee, payment_method, parent, sub, asset_name)
            if e[2] == "지출":
                row = self.expense_table.rowCount()
                self.expense_table.insertRow(row)
                data = [str(e[0]), e[1], e[8], e[11], e[9], e[10], str(e[5]), e[7], e[6]]
                for i, val in enumerate(data):
                    self.expense_table.setItem(row, i, QTableWidgetItem(val or ""))
            else:
                row = self.income_table.rowCount()
                self.income_table.insertRow(row)
                data = [str(e[0]), e[1], e[9], e[10], str(e[5]), e[7]]
                for i, val in enumerate(data):
                    self.income_table.setItem(row, i, QTableWidgetItem(val or ""))

        self.income_table.blockSignals(False)
        self.expense_table.blockSignals(False)
        self.refresh_summary()

    def add_row(self, table):
        table.blockSignals(True)
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 1, QTableWidgetItem(f"{self.year}-{self.month:02d}-01"))
        # Fill zeros for amount column
        amt_col = 6 if table.entry_type == "지출" else 4
        table.setItem(row, amt_col, QTableWidgetItem("0"))
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
        def sum_table(table, col):
            total = 0
            for r in range(table.rowCount()):
                item = table.item(r, col)
                if item:
                    try: total += int(item.text().replace(',', ''))
                    except: pass
            return total
        
        exp = sum_table(self.expense_table, 6)
        inc = sum_table(self.income_table, 4)
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
