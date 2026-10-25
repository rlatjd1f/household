import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QMessageBox, 
                             QHeaderView, QFrame, QComboBox, QDateEdit, QStyledItemDelegate, QLineEdit,
                             QSplitter, QAbstractItemView, QAbstractItemDelegate)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QBrush, QShortcut, QKeySequence
from database import (get_ledger_entries, add_ledger_entry, update_ledger_entry,
                      delete_ledger_entry, get_categories, get_assets)

BUDGET_OVER_COLOR = "#d93025"
BUDGET_OK_COLOR = "#188038"

AMOUNT_PATTERN = re.compile(r"-?\d{1,15}")

def parse_amount(text):
    """'12,000', '12000원', '₩12,000', '-5000'(환불) -> int, 그 외 None"""
    cleaned = re.sub(r"[,\s원₩]", "", text or "")
    return int(cleaned) if AMOUNT_PATTERN.fullmatch(cleaned) else None

class NumericTableWidgetItem(QTableWidgetItem):
    """Custom TableWidgetItem that sorts numerically instead of alphabetically."""
    def __lt__(self, other):
        try:
            v1 = float(self.text().replace(',', ''))
            v2 = float(other.text().replace(',', ''))
            return v1 < v2
        except:
            return super().__lt__(other)

class DateTableWidgetItem(QTableWidgetItem):
    """Date cell that sorts ascending, keeping unsaved new rows below saved rows."""
    def is_new_row(self):
        return self.data(Qt.ItemDataRole.UserRole) == "new"

    def __lt__(self, other):
        if isinstance(other, DateTableWidgetItem) and self.is_new_row() != other.is_new_row():
            return other.is_new_row()
        return self.text() < other.text()

class DateDelegate(QStyledItemDelegate):
    """Delegate that uses QDateEdit with Up/Down adjustment for Date cells."""
    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.setDisplayFormat("yyyy-MM-dd")
        editor.setCalendarPopup(True)
        editor.setCurrentSection(QDateEdit.Section.DaySection)
        return editor

    def setEditorData(self, editor, index):
        date_str = index.data(Qt.ItemDataRole.EditRole) or index.data(Qt.ItemDataRole.DisplayRole)
        if date_str:
            editor.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
        QTimer.singleShot(0, lambda: editor.setCurrentSection(QDateEdit.Section.DaySection))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.date().toString("yyyy-MM-dd"), Qt.ItemDataRole.EditRole)

class StyledComboBox(QComboBox):
    """Enhanced ComboBox that opens on Arrow keys."""
    def __init__(self, parent=None, row=None, col=None, spreadsheet=None):
        super().__init__(parent)
        self.row_idx = row
        self.col_idx = col
        self.spreadsheet = spreadsheet
        # 엔터로 입력한 글자가 목록 항목으로 추가되지 않도록 함
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.currentTextChanged.connect(self.setToolTip)

    def show_text_start(self):
        # 편집 가능한 콤보는 커서가 끝에 있어 긴 이름의 앞부분이 잘려 보이므로 처음부터 표시
        if self.lineEdit() and not self.lineEdit().hasFocus():
            self.lineEdit().setCursorPosition(0)

    def setCurrentText(self, text):
        super().setCurrentText(text)
        self.show_text_start()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.show_text_start()

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key.Key_Down, Qt.Key.Key_Up] and not self.view().isVisible():
            self.showPopup()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.spreadsheet and not self.view().isVisible():
            super().keyPressEvent(event)
            index = self.spreadsheet.indexAt(self.pos())
            if index.isValid():
                self.spreadsheet.setCurrentCell(index.row(), index.column())
                self.spreadsheet.move_to_next_row(index.column())
        else:
            super().keyPressEvent(event)

class LedgerSpreadsheet(QTableWidget):
    """A highly customized spreadsheet table with dynamic dropdowns and manual save."""
    def __init__(self, ledger_tab, entry_type, columns):
        self.base_cols = columns
        display_cols = columns + ["저장"]
        super().__init__(0, len(display_cols) + 1)
        self.ledger_tab = ledger_tab
        self.entry_type = entry_type
        self.init_ui(display_cols)

    def init_ui(self, display_cols):
        headers = ["ID"] + display_cols
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        header = self.horizontalHeader()
        # 열 너비는 사용자가 조절할 수 있고, 마지막 텍스트 열(코멘트/소득처)이 남는 공간을 차지
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        if self.entry_type == "지출":
            widths = {1: 92, 2: 100, 3: 110, 4: 132, 5: 118, 6: 95, 7: 105}
            stretch_col, stretch_min = 8, 160
        else:
            widths = {1: 92, 2: 100, 3: 95, 4: 95}
            stretch_col, stretch_min = 5, 100
        for col, width in widths.items():
            self.setColumnWidth(col, width)
        self.stretch_col, self.stretch_min = stretch_col, stretch_min
        self.setColumnWidth(stretch_col, stretch_min)
        header.sectionResized.connect(self.fit_stretch_column)

        save_col = self.columnCount() - 1
        header.setSectionResizeMode(save_col, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(save_col, 44)
        
        self.verticalHeader().setDefaultSectionSize(36) 
        self.verticalHeader().setVisible(False)
        self.setColumnHidden(0, True)
        # 헤더 클릭 정렬은 사용하지 않고 항상 날짜 오름차순으로 유지 (sort_by_date)
        self.setSortingEnabled(False)

        self.date_delegate = DateDelegate(self)
        self.setItemDelegateForColumn(1, self.date_delegate)
        self.itemChanged.connect(self.handle_item_changed)

    def fit_stretch_column(self, *args):
        # 마지막 텍스트 열이 남는 너비를 채우되, 최소 너비 아래로는 줄지 않음 (부족하면 가로 스크롤)
        header = self.horizontalHeader()
        used = sum(self.columnWidth(c) for c in range(self.columnCount())
                   if c != self.stretch_col and not self.isColumnHidden(c))
        width = max(self.stretch_min, self.viewport().width() - used)
        if width != self.columnWidth(self.stretch_col):
            header.blockSignals(True)
            self.setColumnWidth(self.stretch_col, width)
            header.blockSignals(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_stretch_column()

    def sort_by_date(self):
        # 같은 날짜끼리는 기존 순서(입력 순서)를 유지하는 안정 정렬
        self.sortItems(1, Qt.SortOrder.AscendingOrder)

    def handle_item_changed(self, item):
        if self.signalsBlocked(): return
        row = item.row()
        col = item.column()
        
        amt_col = 6 if self.entry_type == "지출" else 4
        if col == amt_col:
            amount = parse_amount(item.text())
            self.blockSignals(True)
            if amount is None:
                # 잘못된 입력은 0으로 바꾸지 않고 직전 값으로 되돌림
                item.setText(item.data(Qt.ItemDataRole.UserRole) or "0")
            else:
                item.setText(format(amount, ','))
                item.setData(Qt.ItemDataRole.UserRole, item.text())
            self.blockSignals(False)
            if amount is None:
                QMessageBox.warning(self, "금액 입력", "금액은 숫자로 입력해 주세요.\n환불·취소는 -5000 처럼 마이너스로 입력할 수 있습니다.")
                return

        self.set_save_status(row, False)

    def set_save_status(self, row, is_saved):
        save_col = self.columnCount() - 1
        btn = self.cellWidget(row, save_col)
        if isinstance(btn, QPushButton):
            btn.setText("✅" if is_saved else "❓")

    def save_row_to_db(self, row):
        if self.signalsBlocked() or row < 0 or row >= self.rowCount(): return
        
        id_item = self.item(row, 0)
        if not id_item: return
        entry_id_text = id_item.text().strip()
        entry_id = int(entry_id_text) if entry_id_text else None
        
        try:
            if self.entry_type == "지출":
                date = self.get_val(row, 1)
                pay_method = self.get_val(row, 2)
                asset_name = self.get_val(row, 3)
                parent = self.get_val(row, 4)
                sub = self.get_val(row, 5)
                amount = self.get_int(row, 6)
                payee = self.get_val(row, 7)
                memo = self.get_val(row, 8)
            else:
                date = self.get_val(row, 1)
                parent = self.get_val(row, 2)
                sub = self.get_val(row, 3)
                amount = self.get_int(row, 4)
                payee = self.get_val(row, 5)
                pay_method, asset_name, memo = "", "", ""

            cat_id = self.ledger_tab.resolve_category_id(self.entry_type, parent, sub)
            asset_id = self.ledger_tab.resolve_asset_id(self.entry_type, pay_method, asset_name)

            if not date:
                QMessageBox.warning(self, "저장 실패", "날짜를 입력해 주세요.")
                return False
            if not self.confirm_row_save(date, parent, sub, cat_id, pay_method, asset_name, asset_id):
                return False
            if entry_id:
                saved = update_ledger_entry(entry_id, date, self.entry_type, cat_id, asset_id, amount, memo, payee, pay_method)
            else:
                new_id = add_ledger_entry(self.ledger_tab.hid, date, self.entry_type, cat_id, asset_id, amount, memo, payee, pay_method)
                saved = bool(new_id)
                if new_id:
                    self.blockSignals(True)
                    self.setItem(row, 0, QTableWidgetItem(str(new_id)))
                    self.blockSignals(False)
            if not saved:
                QMessageBox.warning(self, "저장 실패", "내역을 저장하지 못했습니다.")
                return False

            if not self.ledger_tab.is_in_this_month(date):
                # 다른 달로 저장된 내역은 해당 월 가계부에서 보이므로 이 표에서 제거
                self.removeRow(row)
                self.ledger_tab.refresh_summary()
                return True

            self.blockSignals(True)
            date_item = self.item(row, 1)
            if date_item: date_item.setData(Qt.ItemDataRole.UserRole, None)
            saved_id_item = self.item(row, 0)
            self.sort_by_date()
            self.blockSignals(False)
            self.set_save_status(saved_id_item.row(), True)
            self.scrollToItem(saved_id_item)
            self.ledger_tab.refresh_summary()
            return True
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"저장 중 오류 발생: {e}")
            return False

    def confirm_row_save(self, date, parent, sub, cat_id, pay_method, asset_name, asset_id):
        """분류가 없거나 다른 달 날짜인 경우 저장 전에 확인"""
        notes = []
        if cat_id is None:
            if parent or sub:
                notes.append(f"'{parent} > {sub}' 분류가 설정에 없어 분류 없이 저장됩니다.")
            else:
                notes.append("대분류/항목이 비어 있어 분류 없이 저장됩니다. (리포트 분류별 통계에서 빠집니다)")
        if self.entry_type == "지출" and (pay_method or asset_name) and asset_id is None:
            notes.append(f"'{pay_method} > {asset_name}' 결제수단이 설정에 없습니다.")
        if not self.ledger_tab.is_in_this_month(date):
            notes.append(f"날짜가 {date[:4]}년 {int(date[5:7])}월이라 저장하면 해당 월 가계부로 이동합니다.")
        if not notes:
            return True
        message = f"{date} 내역\n\n" + "\n".join(f"• {note}" for note in notes) + "\n\n그대로 저장할까요?"
        reply = QMessageBox.question(self, "저장 확인", message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes

    def unsaved_rows(self):
        save_col = self.columnCount() - 1
        return [r for r in range(self.rowCount())
                if isinstance(self.cellWidget(r, save_col), QPushButton) and self.cellWidget(r, save_col).text() == "❓"]

    def save_all_rows(self):
        """저장하지 않은 행을 모두 저장하고 (저장, 실패) 건수를 반환"""
        # 저장 중 정렬/이동으로 행 번호가 바뀌므로 날짜 셀 항목으로 행을 추적
        items = [self.item(r, 1) for r in self.unsaved_rows()]
        saved = failed = 0
        for item in items:
            if self.save_row_to_db(item.row()): saved += 1
            else: failed += 1
        return saved, failed

    def move_to_next_row(self, col):
        """엑셀처럼 아래 행으로 이동하고, 마지막 행이면 새 행을 추가"""
        col = max(col, 1)
        row = self.currentRow()
        next_row = next((r for r in range(row + 1, self.rowCount()) if not self.isRowHidden(r)), None)
        if next_row is None:
            self.ledger_tab.add_row(self)
            next_row = self.rowCount() - 1
        self.setCurrentCell(next_row, col)
        widget = self.cellWidget(next_row, col)
        (widget or self).setFocus()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.state() != QAbstractItemView.State.EditingState:
            self.move_to_next_row(self.currentColumn())
            return
        super().keyPressEvent(event)

    def closeEditor(self, editor, hint):
        super().closeEditor(editor, hint)
        # 셀 편집 중 엔터(SubmitModelCache)로 입력을 마치면 아래 행으로 이동
        if hint == QAbstractItemDelegate.EndEditHint.SubmitModelCache:
            col = self.currentColumn()
            QTimer.singleShot(0, lambda: self.move_to_next_row(col))

    def get_val(self, row, col):
        widget = self.cellWidget(row, col)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        item = self.item(row, col)
        return item.text().strip() if item else ""

    def get_int(self, row, col):
        text = self.get_val(row, col).replace(',', '')
        try:
            return int(text)
        except:
            return 0

class LedgerTab(QWidget):
    def __init__(self, hid=None, month=1, year=None):
        super().__init__()
        self.hid = hid
        self.month = month
        self.year = year or QDate.currentDate().year()
        self.category_color_map = {}
        self.category_cache = {}
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        self.summary_label = QLabel("월 예산: 0 | 지출: 0 | 남은 예산: 0")
        self.summary_label.setObjectName("SummaryLabel")
        layout.addWidget(self.summary_label)

        # 지출/소득 표 사이 경계를 끌어서 너비 비율을 조절할 수 있음
        content_layout = QSplitter(Qt.Orientation.Horizontal)
        content_layout.setChildrenCollapsible(False)
        content_layout.setHandleWidth(12)
        content_layout.setStyleSheet("QSplitter::handle { background: transparent; }")
        exp_columns = ["소비날짜", "결제수단", "수단명", "대분류", "항목", "지출금액", "사용처", "코멘트"]
        self.expense_box = self.create_section("💸 소비 내역 (지출)", "지출", exp_columns)
        inc_columns = ["소득날짜", "대분류", "항목", "소득 금액", "소득처"]
        self.income_box = self.create_section("💰 소득 내역 (수입)", "수입", inc_columns)

        content_layout.addWidget(self.expense_box)
        content_layout.addWidget(self.income_box)
        content_layout.setStretchFactor(0, 13)
        content_layout.setStretchFactor(1, 7)
        layout.addWidget(content_layout, 1)

        save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        save_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        save_shortcut.activated.connect(self.save_all)

    def is_in_this_month(self, date):
        return date.startswith(f"{self.year}-{self.month:02d}-")

    def save_all(self, tables=None):
        saved = failed = 0
        for table in tables or (self.expense_table, self.income_table):
            s, f = table.save_all_rows()
            saved += s; failed += f
        if failed:
            QMessageBox.warning(self, "모두 저장", f"{saved}건을 저장했고 {failed}건은 저장하지 않았습니다.")

    def create_section(self, title, etype, columns):
        box = QFrame()
        box.setObjectName("ContentCard")
        vbox = QVBoxLayout(box)
        
        lbl_layout = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {'#d93025' if etype=='지출' else '#1a73e8'};")
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("검색/필터...")
        search_input.setFixedWidth(150)
        search_input.setStyleSheet("font-size: 11px; padding: 4px;")
        
        lbl_layout.addWidget(lbl)
        lbl_layout.addStretch()
        lbl_layout.addWidget(search_input)
        vbox.addLayout(lbl_layout)
        
        table = LedgerSpreadsheet(self, etype, columns)
        if etype == "지출": self.expense_table = table
        else: self.income_table = table
        
        search_input.textChanged.connect(lambda t, tbl=table: self.filter_table(tbl, t))
        
        btns = QHBoxLayout()
        add_btn = QPushButton(f"+ {etype} 행 추가")
        add_btn.clicked.connect(lambda chk, tbl=table: self.add_row(tbl))
        del_btn = QPushButton("- 삭제")
        del_btn.setObjectName("DeleteBtn")
        del_btn.clicked.connect(lambda chk, tbl=table: self.delete_row(tbl))
        
        save_all_btn = QPushButton("💾 모두 저장")
        save_all_btn.setToolTip("저장하지 않은 행(❓)을 모두 저장합니다. (Ctrl+S: 지출·소득 모두)")
        save_all_btn.clicked.connect(lambda chk, tbl=table: self.save_all([tbl]))

        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addStretch()
        btns.addWidget(save_all_btn)
        
        vbox.addWidget(table)
        vbox.addLayout(btns)
        return box

    def filter_table(self, table, text):
        for row in range(table.rowCount()):
            match = False
            for col in range(1, table.columnCount() - 1):
                if text.lower() in table.get_val(row, col).lower():
                    match = True
                    break
            table.setRowHidden(row, not match)
        self.refresh_summary()

    def has_unsaved_changes(self):
        return any(table.unsaved_rows() for table in (self.expense_table, self.income_table))

    def set_year(self, year, refresh=True):
        self.year = year
        if refresh: self.refresh_data()

    def refresh_data(self):
        if self.hid is None: return
        self.refresh_category_colors()
        self.income_table.blockSignals(True)
        self.expense_table.blockSignals(True)
        
        entries = get_ledger_entries(self.hid, self.year, self.month)
        self.income_table.setRowCount(0)
        self.expense_table.setRowCount(0)
        
        for e in entries:
            if e[2] == "지출":
                row = self.expense_table.rowCount()
                self.expense_table.insertRow(row)
                data = [str(e[0]), e[1], e[8], e[11], e[9], e[10], format(e[5], ','), e[7], e[6]]
                for i, val in enumerate(data):
                    self.set_table_item(self.expense_table, row, i, val)
                self.add_save_button(self.expense_table, row, True)
                self.apply_row_color(self.expense_table, row, e[12] if len(e) > 12 else None)
            else:
                row = self.income_table.rowCount()
                self.income_table.insertRow(row)
                data = [str(e[0]), e[1], e[9], e[10], format(e[5], ','), e[7]]
                for i, val in enumerate(data):
                    self.set_table_item(self.income_table, row, i, val)
                self.add_save_button(self.income_table, row, True)
                self.apply_row_color(self.income_table, row, e[12] if len(e) > 12 else None)
                
        self.income_table.blockSignals(False)
        self.expense_table.blockSignals(False)
        self.income_table.sort_by_date()
        self.expense_table.sort_by_date()
        self.refresh_summary()

    def refresh_category_colors(self):
        self.category_cache = {db_type: [] for db_type in ["소비", "소득", "결제수단"]}
        for category in get_categories(self.hid):
            if category[1] in self.category_cache:
                self.category_cache[category[1]].append(category)
        self.category_color_map = {}
        for db_type in ["소비", "소득"]:
            for category in self.category_cache[db_type]:
                if len(category) > 4 and category[4]:
                    self.category_color_map[(category[1], category[2], category[3])] = category[4]

    def cached_categories(self, db_type):
        return self.category_cache.get(db_type, [])

    def get_text_color_for_background(self, color):
        qcolor = QColor(color)
        if not qcolor.isValid():
            return None
        luminance = (0.299 * qcolor.red() + 0.587 * qcolor.green() + 0.114 * qcolor.blue())
        return QColor("#202124") if luminance > 150 else QColor("#ffffff")

    def apply_row_color(self, table, row, color):
        text_color = self.get_text_color_for_background(color) if color else None
        bg_color = QColor(color) if color else None

        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item:
                if bg_color and bg_color.isValid():
                    item.setBackground(bg_color)
                    if text_color:
                        item.setForeground(text_color)
                else:
                    item.setBackground(QBrush())
                    item.setForeground(QBrush())

            widget = table.cellWidget(row, col)
            if isinstance(widget, QComboBox):
                if bg_color and bg_color.isValid():
                    text = text_color.name() if text_color else "#202124"
                    widget.setStyleSheet(f"QComboBox {{ background-color: {color}; color: {text}; }}")
                elif widget.styleSheet():
                    # setStyleSheet는 위젯 스타일을 다시 계산해 느리므로 색을 지울 때만 호출
                    widget.setStyleSheet("")
            elif isinstance(widget, QPushButton) and widget.objectName() == "SaveBtn":
                if bg_color and bg_color.isValid():
                    text = text_color.name() if text_color else "#202124"
                    widget.setStyleSheet(f"background-color: {color}; color: {text};")
                elif widget.styleSheet():
                    widget.setStyleSheet("")

    def apply_row_color_from_values(self, table, row):
        if table.entry_type == "지출":
            db_type = "소비"
            parent = table.get_val(row, 4)
            sub = table.get_val(row, 5)
        else:
            db_type = "소득"
            parent = table.get_val(row, 2)
            sub = table.get_val(row, 3)
        self.apply_row_color(table, row, self.category_color_map.get((db_type, parent, sub)))

    def set_table_item(self, table, row, col, val):
        if col == 0:
            table.setItem(row, col, QTableWidgetItem(val))
            return
        
        amt_col = 6 if table.entry_type == "지출" else 4
        combos = {"지출": {2: "결제수단", 3: "수단명", 4: "소비_대", 5: "소비_중"}, "수입": {2: "소득_대", 3: "소득_중"}}
        
        if col in combos[table.entry_type]:
            item = QTableWidgetItem(val or "")
            table.setItem(row, col, item)
            combo = StyledComboBox(row=row, col=col, spreadsheet=table)
            combo.setEditable(True)
            self.populate_combo(combo, combos[table.entry_type][col], table, row, col)
            combo.setCurrentText(val or "")
            
            et = table.entry_type
            if et == "지출":
                if col == 2:
                    combo.currentTextChanged.connect(lambda t, r=row, tbl=table: self.handle_combo_change(tbl, r, col, 3, "수단명", t))
                elif col == 4:
                    combo.currentTextChanged.connect(lambda t, r=row, tbl=table: self.handle_combo_change(tbl, r, col, 5, "소비_중", t))
                else:
                    combo.currentTextChanged.connect(lambda t, tbl=table, cmb=combo, c=col: self.handle_combo_value_change(tbl, cmb, c, t))
            elif et == "수입" and col == 2:
                combo.currentTextChanged.connect(lambda t, r=row, tbl=table: self.handle_combo_change(tbl, r, col, 3, "소득_중", t))
            else:
                combo.currentTextChanged.connect(lambda t, tbl=table, cmb=combo, c=col: self.handle_combo_value_change(tbl, cmb, c, t))
            
            table.setCellWidget(row, col, combo)
        elif col == 1:
            table.setItem(row, col, DateTableWidgetItem(val or ""))
        elif col == amt_col:
            item = NumericTableWidgetItem(val or "0")
            item.setData(Qt.ItemDataRole.UserRole, val or "0")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row, col, item)
        else:
            table.setItem(row, col, QTableWidgetItem(val or ""))

    def add_save_button(self, table, row, is_saved=True):
        btn = QPushButton("✅" if is_saved else "❓")
        btn.setObjectName("SaveBtn")
        btn.clicked.connect(lambda: table.save_row_to_db(table.indexAt(table.sender().pos()).row()))
        table.setCellWidget(row, table.columnCount() - 1, btn)

    def handle_combo_value_change(self, table, combo, col, text):
        row = table.indexAt(combo.pos()).row()
        if row < 0:
            return
        item = table.item(row, col)
        if item:
            item.setText(text)
        table.set_save_status(row, False)
        self.apply_row_color_from_values(table, row)

    def handle_combo_change(self, table, row, col, child_col, ctype, text):
        sender = self.sender()
        if not sender: return
        visual_row = table.indexAt(sender.pos()).row()
        item = table.item(visual_row, col)
        if item: item.setText(text)
        table.set_save_status(visual_row, False)
        if child_col is not None:
            self.refresh_child_combo(table, visual_row, child_col, ctype, text)
        self.apply_row_color_from_values(table, visual_row)

    def refresh_child_combo(self, table, row, child_col, ctype, parent_val):
        child_combo = table.cellWidget(row, child_col)
        if isinstance(child_combo, QComboBox):
            child_combo.blockSignals(True)
            child_combo.clear()
            if ctype == "수단명":
                items = [c[3] for c in self.cached_categories("결제수단") if c[2] == parent_val]
            elif ctype == "소비_중":
                items = [c[3] for c in self.cached_categories("소비") if c[2] == parent_val]
            elif ctype == "소득_중":
                items = [c[3] for c in self.cached_categories("소득") if c[2] == parent_val]
            else:
                items = []
            child_combo.addItems(items)
            child_combo.setCurrentIndex(-1)
            child_item = table.item(row, child_col)
            if child_item: child_item.setText("")
            child_combo.blockSignals(False)

    def populate_combo(self, combo, ctype, table, row, col):
        if ctype == "결제수단":
            items = sorted(list(set(c[2] for c in self.cached_categories("결제수단"))))
        elif ctype == "수단명":
            p = table.get_val(row, 2)
            items = [c[3] for c in self.cached_categories("결제수단") if c[2] == p]
        elif ctype == "소비_대":
            items = sorted(list(set(c[2] for c in self.cached_categories("소비"))))
        elif ctype == "소비_중":
            p = table.get_val(row, 4)
            items = [c[3] for c in self.cached_categories("소비") if c[2] == p]
        elif ctype == "소득_대":
            items = sorted(list(set(c[2] for c in self.cached_categories("소득"))))
        elif ctype == "소득_중":
            p = table.get_val(row, 2)
            items = [c[3] for c in self.cached_categories("소득") if c[2] == p]
        else:
            items = []
        combo.addItems(items)

    def add_row(self, table):
        table.blockSignals(True)
        # 새 행은 항상 마지막 행 아래에 생성하고, 저장 시 날짜 순서 자리로 이동
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(""))
        today = QDate.currentDate()
        day = today.day() if (today.year(), today.month()) == (self.year, self.month) else 1
        date_item = DateTableWidgetItem(f"{self.year}-{self.month:02d}-{day:02d}")
        date_item.setData(Qt.ItemDataRole.UserRole, "new")
        table.setItem(row, 1, date_item)
        for col in range(2, table.columnCount() - 1):
            dv = "0" if (table.entry_type=="지출" and col==6) or (table.entry_type=="수입" and col==4) else ""
            self.set_table_item(table, row, col, dv)
        self.add_save_button(table, row, False)
        table.blockSignals(False)
        table.scrollToBottom()
        table.setCurrentCell(row, 1)

    def delete_row(self, table):
        row = table.currentRow()
        if row < 0: return
        confirm = QMessageBox.question(self, "삭제 확인", "선택한 행을 삭제하시겠습니까?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes: return
        id_item = table.item(row, 0)
        if id_item and id_item.text():
            delete_ledger_entry(int(id_item.text()))
        table.removeRow(row)
        self.refresh_summary()

    def refresh_summary(self):
        from database import get_detailed_budgets
        budget_data = get_detailed_budgets(self.hid, self.year)
        monthly_total_budget = 0
        for cat_data in budget_data.values():
            monthly_total_budget += cat_data.get(self.month, 0)
        def sum_table(table, col, visible_only=False):
            return sum(table.get_int(r, col) for r in range(table.rowCount())
                       if not (visible_only and table.isRowHidden(r)))
        # 예산 비교는 검색 필터와 관계없이 이번 달 전체 내역 기준
        exp = sum_table(self.expense_table, 6)
        income = sum_table(self.income_table, 4)
        remaining = monthly_total_budget - exp
        # 예산 초과: 빨간색, 초과하지 않음: 초록색
        status_color = BUDGET_OVER_COLOR if remaining < 0 else BUDGET_OK_COLOR
        text = (
            f"<span style='color:#1a73e8;'>{self.year}년 {self.month}월</span> | "
            f"월 예산: {monthly_total_budget:,} | 지출: <span style='color:{status_color};'>{exp:,}</span> | "
            f"남은 예산: <span style='color:{status_color};'>{remaining:,}</span> | 수입: {income:,}"
        )
        if any(table.isRowHidden(r) for table in (self.expense_table, self.income_table) for r in range(table.rowCount())):
            text += (f" <span style='color:#5f6368; font-weight:normal;'>| 🔍 검색 결과: 지출 {sum_table(self.expense_table, 6, True):,}"
                     f" · 수입 {sum_table(self.income_table, 4, True):,}</span>")
        self.summary_label.setText(text)

    def resolve_category_id(self, etype, p, s):
        db_type = "소비" if etype == "지출" else "소득"
        for c in self.cached_categories(db_type):
            if c[2] == p and c[3] == s: return c[0]
        return None

    def resolve_asset_id(self, etype, pm, an):
        if etype == "지출":
            for c in self.cached_categories("결제수단"):
                if c[2] == pm and c[3] == an: return c[0]
        return None
