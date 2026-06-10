from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLineEdit, QPushButton, QLabel, 
                             QMessageBox, QHeaderView, QScrollArea, QFrame, QGridLayout)
from PyQt6.QtCore import Qt
from database import add_category, get_categories, delete_category

class CategorySection(QFrame):
    """A hierarchical tree section for category management."""
    def __init__(self, title, db_type, parent_tab):
        super().__init__()
        self.title = title
        self.db_type = db_type
        self.parent_tab = parent_tab
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            CategorySection { border-radius: 12px; }
            QLabel#SectionTitle { font-weight: 600; font-size: 16px; padding: 10px 5px; }
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

        # Tree Widget (Hierarchical)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["분류명"])
        self.tree.header().setStretchLastSection(True)
        self.tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.tree.setFixedHeight(250)
        layout.addWidget(self.tree)

        # Inputs
        input_layout = QHBoxLayout()
        self.parent_input = QLineEdit()
        self.parent_input.setPlaceholderText("대분류 (예: 식비)")
        self.sub_input = QLineEdit()
        self.sub_input.setPlaceholderText("중분류 (예: 외식)")
        
        add_btn = QPushButton("추가")
        add_btn.setFixedWidth(80)
        add_btn.clicked.connect(self.handle_add)
        
        del_btn = QPushButton("삭제")
        del_btn.setObjectName("DeleteBtn")
        del_btn.setFixedWidth(80)
        del_btn.clicked.connect(self.handle_delete)

        input_layout.addWidget(self.parent_input)
        input_layout.addWidget(self.sub_input)
        input_layout.addWidget(add_btn)
        input_layout.addWidget(del_btn)
        layout.addLayout(input_layout)

    def load_data(self):
        categories = get_categories(self.db_type)
        self.tree.clear()
        
        # Group by parent
        grouped = {}
        for cat in categories:
            # cat: (id, type, parent, sub)
            parent = cat[2]
            if parent not in grouped:
                grouped[parent] = []
            grouped[parent].append(cat)

        for parent_name, subs in sorted(grouped.items()):
            parent_item = QTreeWidgetItem(self.tree, [parent_name])
            parent_item.setFlags(parent_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            
            for sub in sorted(subs, key=lambda x: x[3]):
                sub_item = QTreeWidgetItem(parent_item, [sub[3]])
                sub_item.setData(0, Qt.ItemDataRole.UserRole, sub[0]) # Store ID
            
            parent_item.setExpanded(True)

    def handle_add(self):
        parent = self.parent_input.text().strip()
        sub = self.sub_input.text().strip()
        if not parent or not sub:
            QMessageBox.warning(self, "경고", f"{self.title}의 대분류와 중분류를 모두 입력하세요.")
            return

        if add_category(self.db_type, parent, sub):
            # Only clear sub_input to make adding multiple sub-categories easier
            self.sub_input.clear()
            self.load_data()
        else:
            QMessageBox.warning(self, "오류", "이미 존재하는 항목이거나 오류가 발생했습니다.")

    def handle_delete(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "경고", "삭제할 분류를 선택하세요.")
            return

        cat_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        if cat_id is None:
            QMessageBox.warning(self, "안내", "대분류 자체는 삭제할 수 없습니다. 소속된 모든 중분류를 삭제하면 자동으로 사라지거나, 기능상 중분류를 선택해 삭제해 주세요.")
            return

        confirm = QMessageBox.question(self, "확인", f"'{item.text(0)}' 분류를 삭제하시겠습니까?", 
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
        content_widget.setObjectName("ScrollContent")
        self.grid_layout = QGridLayout(content_widget)
        self.grid_layout.setSpacing(30)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)

        # Define categories and add in 2x2 grid
        self.sections = [
            CategorySection("💸 소비 항목 관리", "소비", self),
            CategorySection("💰 소득 항목 관리", "소득", self),
            CategorySection("💳 결제수단 관리", "결제수단", self),
            CategorySection("🏦 자본/부채 관리", "자본", self)
        ]

        self.grid_layout.addWidget(self.sections[0], 0, 0)
        self.grid_layout.addWidget(self.sections[1], 0, 1)
        self.grid_layout.addWidget(self.sections[2], 1, 0)
        self.grid_layout.addWidget(self.sections[3], 1, 1)
        
        # Ensure grid items stay at the top if window is large
        self.grid_layout.setRowStretch(2, 1)
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def load_data(self):
        for section in self.sections:
            section.load_data()
