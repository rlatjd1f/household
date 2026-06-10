from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QPushButton, QLabel, 
                             QMessageBox, QHeaderView, QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from database import add_category, get_categories, delete_category

class CategorySection(QFrame):
    """A reusable section for each category type (e.g., 소비, 소득)."""
    def __init__(self, title, db_type, parent_tab):
        super().__init__()
        self.title = title
        self.db_type = db_type
        self.parent_tab = parent_tab
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            CategorySection { 
                border-radius: 12px; 
            }
            QLabel#SectionTitle {
                font-weight: 600;
                font-size: 16px;
                padding: 10px 5px;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Title
        header = QLabel(self.title)
        header.setObjectName("SectionTitle")
        layout.addWidget(header)

        # Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "대분류", "중분류"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setFixedHeight(200)
        layout.addWidget(self.table)

        # Inputs and Buttons
        input_layout = QHBoxLayout()
        self.parent_input = QLineEdit()
        self.parent_input.setPlaceholderText("대분류")
        self.sub_input = QLineEdit()
        self.sub_input.setPlaceholderText("중분류")
        
        add_btn = QPushButton("추가")
        add_btn.setFixedWidth(60)
        add_btn.clicked.connect(self.handle_add)
        
        del_btn = QPushButton("삭제")
        del_btn.setObjectName("DeleteBtn")
        del_btn.setFixedWidth(60)
        del_btn.clicked.connect(self.handle_delete)

        input_layout.addWidget(self.parent_input)
        input_layout.addWidget(self.sub_input)
        input_layout.addWidget(add_btn)
        input_layout.addWidget(del_btn)
        layout.addLayout(input_layout)

    def load_data(self):
        categories = get_categories(self.db_type)
        self.table.setRowCount(0)
        for cat in categories:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(cat[0])))
            self.table.setItem(row, 1, QTableWidgetItem(cat[2]))
            self.table.setItem(row, 2, QTableWidgetItem(cat[3]))

    def handle_add(self):
        parent = self.parent_input.text().strip()
        sub = self.sub_input.text().strip()
        if not parent or not sub:
            QMessageBox.warning(self, "경고", f"{self.title}의 대분류와 중분류를 입력하세요.")
            return

        if add_category(self.db_type, parent, sub):
            self.parent_input.clear()
            self.sub_input.clear()
            self.load_data()
        else:
            QMessageBox.warning(self, "오류", "이미 존재하는 항목이거나 오류가 발생했습니다.")

    def handle_delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "경고", "삭제할 항목을 선택하세요.")
            return

        cat_id = int(self.table.item(row, 0).text())
        confirm = QMessageBox.question(self, "확인", "정말 삭제하시겠습니까?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            delete_category(cat_id)
            self.load_data()

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Scroll Area for all sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(20)

        # Define categories
        self.sections = [
            CategorySection("💸 소비 항목 관리", "소비", self),
            CategorySection("💰 소득 항목 관리", "소득", self),
            CategorySection("💳 결제수단 관리", "결제수단", self),
            CategorySection("🏦 자본/부채 관리", "자본", self)
        ]

        for section in self.sections:
            self.content_layout.addWidget(section)
        
        self.content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def load_data(self):
        for section in self.sections:
            section.load_data()
