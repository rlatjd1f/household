from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLineEdit, QPushButton, QLabel, 
                             QMessageBox, QHeaderView, QScrollArea, QFrame, QGridLayout, QMenu,
                             QApplication, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QIcon, QPixmap, QFont
from database import (add_category, get_categories, delete_category, 
                      delete_category_by_parent, update_category_parent_name, update_category_sub_name,
                      update_category_color)

class ColorPlane(QWidget):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, color):
        super().__init__()
        self.setFixedSize(230, 200)
        self.hue = 210
        self.saturation = 128
        self.value = 255
        self.set_color(color)

    def set_color(self, color):
        if color and color.isValid():
            hue, saturation, value, _ = color.getHsv()
            self.hue = hue if hue >= 0 else 0
            self.saturation = saturation
            self.value = value
        self.update()

    def set_hue(self, hue):
        self.hue = hue
        self.update()
        self.colorChanged.emit(self.current_color())

    def current_color(self):
        return QColor.fromHsv(self.hue, self.saturation, self.value)

    def paintEvent(self, event):
        image = QImage(self.width(), self.height(), QImage.Format.Format_RGB32)
        for x in range(self.width()):
            saturation = int(255 * x / max(1, self.width() - 1))
            for y in range(self.height()):
                value = int(255 * (1 - y / max(1, self.height() - 1)))
                image.setPixelColor(x, y, QColor.fromHsv(self.hue, saturation, value))

        painter = QPainter(self)
        painter.drawImage(0, 0, image)
        marker_x = int(self.saturation / 255 * self.width())
        marker_y = int((1 - self.value / 255) * self.height())
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(marker_x - 8, marker_y, marker_x + 8, marker_y)
        painter.drawLine(marker_x, marker_y - 8, marker_x, marker_y + 8)
        painter.setPen(QPen(Qt.GlobalColor.white, 1))
        painter.drawEllipse(marker_x - 6, marker_y - 6, 12, 12)

    def mousePressEvent(self, event):
        self.update_from_position(event.position().x(), event.position().y())

    def mouseMoveEvent(self, event):
        self.update_from_position(event.position().x(), event.position().y())

    def update_from_position(self, x, y):
        x = min(max(0, int(x)), self.width())
        y = min(max(0, int(y)), self.height())
        self.saturation = int(255 * x / max(1, self.width()))
        self.value = int(255 * (1 - y / max(1, self.height())))
        self.update()
        self.colorChanged.emit(self.current_color())

class HueBar(QWidget):
    hueChanged = pyqtSignal(int)

    def __init__(self, hue):
        super().__init__()
        self.hue = max(0, min(359, int(hue)))
        self.setFixedSize(22, 200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_hue(self, hue):
        self.hue = max(0, min(359, int(hue)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        for y in range(self.height()):
            hue = int(359 * y / max(1, self.height() - 1))
            painter.setPen(QColor.fromHsv(hue, 255, 255))
            painter.drawLine(6, y, 16, y)

        painter.setPen(QPen(QColor("#dadce0"), 1))
        painter.drawRect(5, 0, 12, self.height() - 1)

        marker_y = int(self.hue / 359 * (self.height() - 1))
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(2, marker_y, 20, marker_y)
        painter.setPen(QPen(QColor("#202124"), 1))
        painter.drawLine(2, marker_y + 2, 20, marker_y + 2)

    def mousePressEvent(self, event):
        self.update_from_y(event.position().y())

    def mouseMoveEvent(self, event):
        self.update_from_y(event.position().y())

    def update_from_y(self, y):
        y = min(max(0, int(y)), self.height() - 1)
        self.hue = int(359 * y / max(1, self.height() - 1))
        self.update()
        self.hueChanged.emit(self.hue)


class CategoryColorDialog(QDialog):
    def __init__(self, initial_color, parent=None):
        super().__init__(parent)
        self.setObjectName("CategoryColorDialog")
        self.setWindowTitle("중분류 색상 선택")
        self.setWindowIcon(self.build_emoji_icon("🎨"))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.selected_color = initial_color if initial_color and initial_color.isValid() else QColor("#e8f0fe")
        self.preview_border = "#dadce0"
        self.palette_buttons = []
        self.init_ui()
        self.apply_theme_style()
        self.apply_selected_color(self.selected_color)

    def build_emoji_icon(self, emoji):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setFont(QFont("Segoe UI Emoji", 22))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
        painter.end()
        return QIcon(pixmap)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 14, 16, 12)
        root_layout.setSpacing(12)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(18)

        palette_layout = QVBoxLayout()
        palette_layout.setSpacing(8)
        palette_label = QLabel("기본 색상")
        palette_label.setObjectName("ColorDialogTitle")
        palette_layout.addWidget(palette_label)
        palette_grid = QGridLayout()
        palette_grid.setSpacing(6)
        colors = [
            "#000000", "#800000", "#008000", "#804000", "#00a000", "#808000", "#00ff00", "#80ff00",
            "#000080", "#800080", "#008080", "#aa557f", "#00a080", "#808080", "#00ff80", "#80ff80",
            "#0000ff", "#8000ff", "#0080ff", "#8080ff", "#00a0ff", "#80a0ff", "#00ffff", "#80ffff",
            "#800000", "#ff0000", "#808000", "#ff8000", "#80ff00", "#ffff00", "#00ff00", "#ffff80",
            "#800080", "#ff0080", "#808080", "#ff80a0", "#80a080", "#ffb080", "#80ff80", "#ffff80",
            "#8000ff", "#ff00ff", "#8080ff", "#ff80ff", "#80c0ff", "#ff80c0", "#80ffff", "#ffffff",
        ]
        for index, color in enumerate(colors):
            button = QPushButton()
            button.setObjectName("PaletteColorButton")
            button.setFixedSize(22, 18)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, c=color: self.apply_selected_color(QColor(c)))
            self.palette_buttons.append((button, color))
            palette_grid.addWidget(button, index // 8, index % 8)
        palette_layout.addLayout(palette_grid)
        palette_layout.addStretch()

        picker_layout = QHBoxLayout()
        self.color_plane = ColorPlane(self.selected_color)
        self.color_plane.colorChanged.connect(self.apply_selected_color)
        self.hue_slider = HueBar(self.color_plane.hue)
        self.hue_slider.setObjectName("HueSlider")
        self.hue_slider.hueChanged.connect(self.color_plane.set_hue)
        picker_layout.addWidget(self.color_plane)
        picker_layout.addWidget(self.hue_slider)

        self.preview = QFrame()
        self.preview.setObjectName("ColorPreview")
        self.preview.setFixedSize(74, 174)
        self.preview.setFrameShape(QFrame.Shape.StyledPanel)

        body_layout.addLayout(palette_layout)
        body_layout.addLayout(picker_layout)
        body_layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignTop)
        root_layout.addLayout(body_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.setObjectName("ColorDialogButtons")
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("확인")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root_layout.addWidget(button_box)

    def apply_theme_style(self):
        is_dark = self.is_dark_theme()
        bg = "#202124" if is_dark else "#ffffff"
        text = "#e8eaed" if is_dark else "#3c4043"
        muted = "#bdc1c6" if is_dark else "#5f6368"
        border = "#5f6368" if is_dark else "#dadce0"
        button_bg = "#8ab4f8" if is_dark else "#1a73e8"
        button_hover = "#aecbfa" if is_dark else "#1765cc"
        button_text = "#202124" if is_dark else "#ffffff"
        self.preview_border = border

        self.setStyleSheet(f"""
            QDialog#CategoryColorDialog {{
                background-color: {bg};
                color: {text};
            }}
            QDialog#CategoryColorDialog QLabel {{
                color: {text};
                background: transparent;
            }}
            QLabel#ColorDialogTitle {{
                color: {muted};
                font-size: 12px;
                font-weight: 600;
                padding-bottom: 4px;
            }}
            QFrame#ColorPreview {{
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QPushButton#PaletteColorButton {{
                min-width: 22px;
                min-height: 18px;
                max-width: 22px;
                max-height: 18px;
                padding: 0px;
            }}
            QDialogButtonBox#ColorDialogButtons QPushButton {{
                background-color: {button_bg};
                color: {button_text};
                border: 1px solid {button_bg};
                border-radius: 6px;
                min-width: 78px;
                padding: 8px 18px;
                font-weight: 600;
            }}
            QDialogButtonBox#ColorDialogButtons QPushButton:hover {{
                background-color: {button_hover};
                border-color: {button_hover};
            }}
        """)
        for button, color in self.palette_buttons:
            button.setStyleSheet(
                f"QPushButton#PaletteColorButton {{ background-color: {color}; "
                f"border: 1px solid {border}; border-radius: 3px; padding: 0px; }}"
                f"QPushButton#PaletteColorButton:hover {{ border: 2px solid {button_bg}; }}"
            )

    def is_dark_theme(self):
        widget = self.parentWidget()
        while widget:
            if hasattr(widget, "is_dark_mode"):
                return widget.is_dark_mode
            widget = widget.parentWidget()
        return "background-color: #202124" in (QApplication.instance().styleSheet() or "")

    def apply_selected_color(self, color):
        self.selected_color = color
        hue, saturation, value, _ = color.getHsv()
        if hue >= 0 and self.hue_slider.hue != hue:
            self.hue_slider.blockSignals(True)
            self.hue_slider.set_hue(hue)
            self.hue_slider.blockSignals(False)
            self.color_plane.hue = hue
        self.color_plane.saturation = saturation
        self.color_plane.value = value
        self.color_plane.update()
        self.preview.setStyleSheet(f"QFrame#ColorPreview {{ background-color: {color.name()}; border: 1px solid {self.preview_border}; border-radius: 6px; }}")

class CategorySection(QFrame):
    """A hierarchical tree section for category management."""
    def __init__(self, hid, title, db_type, parent_tab):
        super().__init__()
        self.hid = hid
        self.title = title
        self.db_type = db_type
        self.parent_tab = parent_tab
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            CategorySection { border-radius: 12px; }
            QLabel#SectionTitle { font-weight: 600; font-size: 16px; padding: 10px 5px; }
            QTreeWidget { padding: 6px; }
            QTreeWidget::item { padding: 4px 6px; border-radius: 6px; }
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
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True) 
        self.tree.setIndentation(24)
        self.tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 44)
        self.tree.itemClicked.connect(self.handle_selection_changed)
        
        # Context Menu Policy
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemChanged.connect(self.handle_item_edited)
        
        layout.addWidget(self.tree)

        # Enable Delete Shortcut via Event Filter
        self.tree.installEventFilter(self)

        # Inputs
        input_layout = QHBoxLayout()
        self.parent_input = QLineEdit()
        self.parent_input.setPlaceholderText("대분류")
        self.parent_input.returnPressed.connect(self.handle_add) 
        self.sub_input = QLineEdit()
        self.sub_input.setPlaceholderText("중분류")
        self.sub_input.returnPressed.connect(self.handle_add) 
        
        self.add_btn = QPushButton("추가")
        self.add_btn.setFixedWidth(80)
        self.add_btn.clicked.connect(self.handle_add)
        
        del_btn = QPushButton("삭제")
        del_btn.setObjectName("DeleteBtn")
        del_btn.setFixedWidth(80)
        del_btn.clicked.connect(self.handle_delete)

        input_layout.addWidget(self.parent_input)
        input_layout.addWidget(self.sub_input)
        input_layout.addWidget(self.add_btn)
        input_layout.addWidget(del_btn)
        layout.addLayout(input_layout)

    def is_dark(self):
        return "background-color: #202124" in (QApplication.instance().styleSheet() or "")

    def set_color_button_style(self, button, color):
        bg = color or ("#3c4043" if self.is_dark() else "#ffffff")
        border = "#8ab4f8" if color and self.is_dark() else "#1a73e8" if color else "#dadce0"
        button.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; border: 1px solid {border}; "
            "border-radius: 8px; min-width: 24px; min-height: 18px; }}"
            "QPushButton:hover { border-width: 2px; }"
        )
        button.setToolTip("중분류 색상 선택")

    def handle_color_select(self, category_id, current_color):
        initial = QColor(current_color) if current_color else QColor("#e8f0fe")
        dialog = CategoryColorDialog(initial, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        color = dialog.selected_color
        update_category_color(category_id, color.name())
        self.load_data()

    def show_context_menu(self, position: QPoint):
        item = self.tree.itemAt(position)
        if not item: return
        
        menu = QMenu(self)
        edit_action = menu.addAction("✏️ 이름 수정")
        delete_action = menu.addAction("🗑️ 삭제")
        
        action = menu.exec(self.tree.viewport().mapToGlobal(position))
        
        if action == edit_action:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.tree.editItem(item, 0)
        elif action == delete_action:
            self.handle_delete()

    def handle_item_edited(self, item, column):
        # Prevent recursion and only process user-initiated changes
        if self.signalsBlocked(): return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        # Clean icons/indentation from the edited text
        new_name = item.text(0).replace("📂 ", "").replace("└ ", "").strip()
        
        if not new_name:
            self.load_data() 
            return

        if data["type"] == "parent":
            if new_name != data["name"]:
                update_category_parent_name(self.hid, self.db_type, data["name"], new_name)
        else:
            if new_name != data["name"]:
                update_category_sub_name(data["id"], new_name)
        
        # Reload to refresh formatting and internal data
        self.load_data()

    def eventFilter(self, source, event):
        if event.type() == event.Type.KeyPress and source is self.tree:
            if event.key() == Qt.Key.Key_Delete:
                self.handle_delete()
                return True
        return super().eventFilter(source, event)

    def load_data(self):
        self.tree.blockSignals(True)
        categories = get_categories(self.hid, self.db_type)
        self.tree.clear()
        
        grouped = {}
        for cat in categories:
            parent = cat[2]
            if parent not in grouped:
                grouped[parent] = []
            grouped[parent].append(cat)

        for parent_name, subs in sorted(grouped.items()):
            parent_item = QTreeWidgetItem(self.tree, [f"📂 {parent_name}"])
            parent_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "parent", "name": parent_name})
            parent_item.setFirstColumnSpanned(True)
            parent_item.setSizeHint(0, QSize(0, 34))
            parent_item.setBackground(0, QColor("#e8f0fe") if not self.is_dark() else QColor("#303f56"))
            parent_item.setForeground(0, QColor("#174ea6") if not self.is_dark() else QColor("#aecbfa"))
            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)
            
            for sub in sorted(subs, key=lambda x: x[3]):
                color = sub[4] if len(sub) > 4 else None
                sub_item = QTreeWidgetItem(parent_item, [f"└ {sub[3]}", ""])
                sub_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "sub", "id": sub[0], "parent": parent_name, "name": sub[3], "color": color})
                sub_item.setSizeHint(0, QSize(0, 26))
                sub_item.setForeground(0, QColor("#3c4043") if not self.is_dark() else QColor("#d2d5d9"))
                color_btn = QPushButton()
                color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.set_color_button_style(color_btn, color)
                color_btn.clicked.connect(lambda checked=False, cid=sub[0], c=color: self.handle_color_select(cid, c))
                self.tree.setItemWidget(sub_item, 1, color_btn)
            
            parent_item.setExpanded(True)
        
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
            self.add_btn.setEnabled(False)

    def handle_add(self):
        parent = self.parent_input.text().strip()
        sub = self.sub_input.text().strip()
        if not parent or not sub:
            QMessageBox.warning(self, "경고", "대분류와 중분류를 모두 입력하세요.")
            return

        if add_category(self.hid, self.db_type, parent, sub):
            self.sub_input.clear()
            self.load_data()
            self.sub_input.setFocus() 
        else:
            QMessageBox.warning(self, "오류", "이미 존재하는 항목이거나 오류가 발생했습니다.")

    def handle_delete(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "경고", "삭제할 분류를 선택하세요.")
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data["type"] == "parent":
            confirm = QMessageBox.question(self, "확인", f"대분류 '{data['name']}'와(과) 소속된 모든 중분류를 삭제하시겠습니까?", 
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                delete_category_by_parent(self.hid, self.db_type, data["name"])
                self.load_data()
        else:
            delete_category(data["id"])
            self.load_data()

class SettingsTab(QWidget):
    def __init__(self, hid=None):
        super().__init__()
        self.hid = hid
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        content_widget.setObjectName("ScrollContent")
        self.grid_layout = QGridLayout(content_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)

        self.sections = [
            CategorySection(self.hid, "💸 소비 항목 관리", "소비", self),
            CategorySection(self.hid, "💰 소득 항목 관리", "소득", self),
            CategorySection(self.hid, "💳 결제수단 관리", "결제수단", self),
            CategorySection(self.hid, "🏦 자본/부채 관리", "자본", self)
        ]

        for i, section in enumerate(self.sections):
            self.grid_layout.addWidget(section, 0, i)
        
        self.grid_layout.setRowStretch(0, 1)
        for i in range(4): self.grid_layout.setColumnStretch(i, 1)
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def load_data(self):
        for section in self.sections:
            section.load_data()
