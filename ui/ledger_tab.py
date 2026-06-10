from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QMessageBox, 
                             QHeaderView)
from PyQt6.QtCore import Qt
from database import (get_ledger_entries, add_ledger_entry, update_ledger_entry, 
                      delete_ledger_entry, get_categories, get_assets)
import datetime

class LedgerTab(QWidget):
    def __init__(self, month):
        super().__init__()
        self.month = month
        self.year = 2026 # Default year
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Summary and Controls
        top_layout = QHBoxLayout()
        self.summary_label = QLabel("수입: 0 | 지출: 0 | 잔액: 0")
        self.summary_label.setObjectName("SummaryLabel")
        
        add_btn = QPushButton("+ 행 추가")
        add_btn.clicked.connect(self.add_blank_row)
        
        del_btn = QPushButton("- 선택 삭제")
        del_btn.clicked.connect(self.delete_selected_row)

        top_layout.addWidget(self.summary_label)
        top_layout.addStretch()
        top_layout.addWidget(add_btn)
        top_layout.addWidget(del_btn)
        layout.addLayout(top_layout)

        # Spreadsheet Table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "날짜", "유형", "대분류", "중분류", "자산", "금액", "메모"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setColumnHidden(0, True) # Hide ID
        
        # Connect signal for direct editing
        self.table.itemChanged.connect(self.handle_item_changed)
        
        layout.addWidget(self.table)
        self.setLayout(layout)

    def refresh_data(self):
        self.table.blockSignals(True) # Prevent infinite loops during loading
        entries = get_ledger_entries(self.year, self.month)
        self.table.setRowCount(0)
        
        total_income = 0
        total_expense = 0

        for e in entries:
            # (id, date, type, cat_id, asset_id, amount, memo, parent, sub, asset_name)
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Map columns
            items = [
                (0, str(e[0])), # ID
                (1, e[1]),      # Date
                (2, e[2]),      # Type (수입/지출)
                (3, e[7]),      # Parent Cat
                (4, e[8]),      # Sub Cat
                (5, e[9]),      # Asset Name
                (6, str(e[5])), # Amount
                (7, e[6])       # Memo
            ]
            
            for col, text in items:
                item = QTableWidgetItem(text)
                # Store original IDs for reference
                if col == 0: item.setData(Qt.ItemDataRole.UserRole, e[0])
                if col == 3: item.setData(Qt.ItemDataRole.UserRole, e[3]) # category_id (not exactly right but placeholder)
                if col == 5: item.setData(Qt.ItemDataRole.UserRole, e[4]) # asset_id
                self.table.setItem(row, col, item)

            if e[2] == "수입":
                total_income += e[5]
            else:
                total_expense += e[5]

        self.summary_label.setText(f"수입: {total_income:,} | 지출: {total_expense:,} | 잔액: {total_income - total_expense:,}")
        self.table.blockSignals(False)

    def add_blank_row(self):
        self.table.blockSignals(True)
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Default values
        default_date = f"{self.year}-{self.month:02d}-01"
        self.table.setItem(row, 1, QTableWidgetItem(default_date))
        self.table.setItem(row, 2, QTableWidgetItem("지출"))
        self.table.setItem(row, 6, QTableWidgetItem("0"))
        
        # Scroll to new row
        self.table.scrollToBottom()
        self.table.blockSignals(False)

    def handle_item_changed(self, item):
        row = item.row()
        col = item.column()
        
        # Get ID from hidden column
        id_item = self.table.item(row, 0)
        entry_id = int(id_item.text()) if id_item and id_item.text() else None
        
        # Collect row data
        try:
            date = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            etype = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            parent = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
            sub = self.table.item(row, 4).text() if self.table.item(row, 4) else ""
            asset_name = self.table.item(row, 5).text() if self.table.item(row, 5) else ""
            amount_str = self.table.item(row, 6).text() if self.table.item(row, 6) else "0"
            amount = int(amount_str.replace(',', ''))
            memo = self.table.item(row, 7).text() if self.table.item(row, 7) else ""
            
            # Resolve Category and Asset IDs
            # This is a bit expensive to do on every edit, but necessary for spreadsheet mode
            # without complex delegates. 
            cat_id = self.resolve_category_id(etype, parent, sub)
            asset_id = self.resolve_asset_id(asset_name)
            
            if not cat_id or not asset_id:
                # If not enough data yet, don't save
                return

            if entry_id:
                # Update existing
                update_ledger_entry(entry_id, date, etype, cat_id, asset_id, amount, memo)
            else:
                # Add new
                new_id = add_ledger_entry(date, etype, cat_id, asset_id, amount, memo, "")
                if new_id:
                    self.table.blockSignals(True)
                    self.table.setItem(row, 0, QTableWidgetItem(str(new_id)))
                    self.table.blockSignals(False)
            
            self.refresh_summary()
            
        except Exception as e:
            print(f"Spreadsheet update error: {e}")

    def resolve_category_id(self, etype, parent, sub):
        db_type = "소비" if etype == "지출" else "소득"
        categories = get_categories(db_type)
        for c in categories:
            if c[2] == parent and c[3] == sub:
                return c[0]
        return None

    def resolve_asset_id(self, name):
        assets = get_assets()
        for a in assets:
            if a[1] == name:
                return a[0]
        return None

    def refresh_summary(self):
        total_income = 0
        total_expense = 0
        for row in range(self.table.rowCount()):
            etype_item = self.table.item(row, 2)
            amount_item = self.table.item(row, 6)
            if etype_item and amount_item:
                try:
                    val = int(amount_item.text().replace(',', ''))
                    if etype_item.text() == "수입":
                        total_income += val
                    else:
                        total_expense += val
                except: pass
        self.summary_label.setText(f"수입: {total_income:,} | 지출: {total_expense:,} | 잔액: {total_income - total_expense:,}")

    def delete_selected_row(self):
        row = self.table.currentRow()
        if row < 0: return
        
        id_item = self.table.item(row, 0)
        if id_item and id_item.text():
            entry_id = int(id_item.text())
            confirm = QMessageBox.question(self, "확인", "정말 삭제하시겠습니까?", 
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                delete_ledger_entry(entry_id)
                self.table.removeRow(row)
                self.refresh_summary()
        else:
            self.table.removeRow(row)
