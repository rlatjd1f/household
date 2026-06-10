from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QPushButton, QLabel, 
                             QMessageBox, QHeaderView)
from database import add_asset, get_assets, delete_asset

class AssetTab(QWidget):
    def __init__(self, hid=None):
        super().__init__()
        self.hid = hid
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "자산명", "기초 잔액", "현재 잔액"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        input_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("자산명 (예: 국민은행)")
        self.balance_input = QLineEdit()
        self.balance_input.setPlaceholderText("기초 잔액 (숫자만)")
        
        add_btn = QPushButton("자산 추가")
        add_btn.clicked.connect(self.handle_add)
        
        del_btn = QPushButton("삭제")
        del_btn.setObjectName("DeleteBtn")
        del_btn.clicked.connect(self.handle_delete)

        input_layout.addWidget(QLabel("자산명:"))
        input_layout.addWidget(self.name_input)
        input_layout.addWidget(QLabel("기초 잔액:"))
        input_layout.addWidget(self.balance_input)
        input_layout.addWidget(add_btn)
        input_layout.addWidget(del_btn)
        layout.addLayout(input_layout)

    def load_data(self):
        if self.hid is None: return
        assets = get_assets(self.hid)
        self.table.setRowCount(0)
        for row_data in assets:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            for col_idx, value in enumerate(row_data):
                val_text = format(value, ',') if col_idx >= 2 else str(value)
                item = QTableWidgetItem(val_text)
                self.table.setItem(row_idx, col_idx, item)

    def handle_add(self):
        if self.hid is None: return
        name = self.name_input.text().strip()
        balance_str = self.balance_input.text().strip().replace(',', '')
        if not name or not balance_str: return
        try: balance = int(balance_str)
        except: return

        if add_asset(self.hid, name, balance):
            self.name_input.clear()
            self.balance_input.clear()
            self.load_data()
        else: QMessageBox.warning(self, "오류", "이미 존재하는 자산명이거나 데이터베이스 오류입니다.")

    def handle_delete(self):
        row = self.table.currentRow()
        if row < 0: return
        asset_id = int(self.table.item(row, 0).text())
        confirm = QMessageBox.question(self, "확인", "정말 삭제하시겠습니까?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            delete_asset(asset_id)
            self.load_data()
