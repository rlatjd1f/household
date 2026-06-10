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
        self.tree.setHeaderHidden(True) # Hide the "분류명" header to solve black background bug
        self.tree.setIndentation(20)
        self.tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.tree.setFixedHeight(250)
        self.tree.itemClicked.connect(self.handle_selection_changed)
        layout.addWidget(self.tree)

        # Inputs
        input_layout = QHBoxLayout()
        self.parent_input = QLineEdit()
        self.parent_input.setPlaceholderText("대분류 (예: 식비)")
        self.parent_input.returnPressed.connect(self.handle_add) # Add on Enter
        self.sub_input = QLineEdit()
        self.sub_input.setPlaceholderText("중분류 (예: 외식)")
        self.sub_input.returnPressed.connect(self.handle_add) # Add on Enter
        
        self.add_btn = QPushButton("추가")
        self.add_btn.setFixedWidth(80)
        self.add_btn.clicked.connect(self.handle_add)
        
        self.del_btn = QPushButton("삭제")
        self.del_btn.setObjectName("DeleteBtn")
        self.del_btn.setFixedWidth(80)
        self.del_btn.clicked.connect(self.handle_delete)

        input_layout.addWidget(self.parent_input)
        input_layout.addWidget(self.sub_input)
        input_layout.addWidget(self.add_btn)
        input_layout.addWidget(self.del_btn)
        layout.addLayout(input_layout)

    def load_data(self):
        self.tree.blockSignals(True)
        categories = get_categories(self.db_type)
        self.tree.clear()
        
        # Group by parent
        grouped = {}
        for cat in categories:
            parent = cat[2]
            if parent not in grouped:
                grouped[parent] = []
            grouped[parent].append(cat)

        for parent_name, subs in sorted(grouped.items()):
            # Parent Item Styling
            parent_item = QTreeWidgetItem(self.tree, [f"📂 {parent_name}"])
            parent_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "parent", "name": parent_name})
            
            # Make Parent Font Bold
            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)
            
            for sub in sorted(subs, key=lambda x: x[3]):
                # Sub Item Styling with visual branch prefix
                sub_item = QTreeWidgetItem(parent_item, [f"└ {sub[3]}"])
                sub_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "sub", "id": sub[0], "parent": parent_name, "name": sub[3]})
            
            parent_item.setExpanded(True)
        
        self.parent_input.clear()
        self.sub_input.clear()
        self.add_btn.setEnabled(True)
        self.tree.blockSignals(False)

    def handle_selection_changed(self, item, column):
        if not item: return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data["type"] == "parent":
            self.parent_input.setText(data["name"])
            self.sub_input.clear()
            self.add_btn.setEnabled(True)
        else:
            self.parent_input.setText(data["parent"])
            self.sub_input.setText(data["name"])
            self.add_btn.setEnabled(False) # Disable Add when a sub-item is selected

    def handle_add(self):
        parent = self.parent_input.text().strip()
        sub = self.sub_input.text().strip()
        if not parent or not sub:
            QMessageBox.warning(self, "경고", "대분류와 중분류를 모두 입력하세요.")
            return

        if add_category(self.db_type, parent, sub):
            self.sub_input.clear()
            self.load_data()
            self.sub_input.setFocus() # Keep focus for continuous entry
        else:
            QMessageBox.warning(self, "오류", "이미 존재하는 항목이거나 오류가 발생했습니다.")

    def handle_delete(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "경고", "삭제할 분류를 선택하세요.")
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data["type"] == "parent":
            # Delete entire parent
            confirm = QMessageBox.question(self, "확인", f"대분류 '{data['name']}'와(과) 소속된 모든 중분류를 삭제하시겠습니까?", 
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                self.delete_parent_category(data["name"])
                self.load_data()
        else:
            # Delete specific sub
            confirm = QMessageBox.question(self, "확인", f"중분류 '{data['name']}'을(를) 삭제하시겠습니까?", 
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                delete_category(data["id"])
                self.load_data()

    def delete_parent_category(self, parent_name):
        delete_parent_category_db(self.db_type, parent_name)

def delete_parent_category_db(db_type, parent_name):
    import sqlite3
    from database import DB_NAME
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE type = ? AND parent_category = ?", (db_type, parent_name))
    conn.commit()
    conn.close()

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
