from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QMessageBox, 
                             QHeaderView, QFrame, QComboBox, QDateEdit, QStyledItemDelegate, QLineEdit)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QBrush
from database import (get_ledger_entries, add_ledger_entry, update_ledger_entry, 
                      delete_ledger_entry, get_categories, get_assets)

class NumericTableWidgetItem(QTableWidgetItem):
    """Custom TableWidgetItem that sorts numerically instead of alphabetically."""
    def __lt__(self, other):
        try:
            v1 = float(self.text().replace(',', ''))
            v2 = float(other.text().replace(',', ''))
            return v1 < v2
        except:
            return super().__lt__(other)

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

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key.Key_Down, Qt.Key.Key_Up] and not self.view().isVisible():
            self.showPopup()
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
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(1, 120)
        
        amt_col = 6 if self.entry_type == "지출" else 4
        self.horizontalHeader().setSectionResizeMode(amt_col, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(amt_col, 120)

        save_col = self.columnCount() - 1
        self.horizontalHeader().setSectionResizeMode(save_col, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(save_col, 60)
        
        self.verticalHeader().setDefaultSectionSize(36) 
        self.verticalHeader().setVisible(False)
        self.setColumnHidden(0, True)
        self.setSortingEnabled(True)

        self.date_delegate = DateDelegate(self)
        self.setItemDelegateForColumn(1, self.date_delegate)
        self.itemChanged.connect(self.handle_item_changed)

    def handle_item_changed(self, item):
        if self.signalsBlocked(): return
        row = item.row()
        col = item.column()
        
        amt_col = 6 if self.entry_type == "지출" else 4
        if col == amt_col:
            self.blockSignals(True)
            text = item.text().replace(',', '').strip()
            if text.isdigit():
                item.setText(format(int(text), ','))
            else:
                item.setText("0")
            self.blockSignals(False)

        self.set_save_status(row, False)

    def set_save_status(self, row, is_saved):
        save_col = self.columnCount() - 1
        btn = self.cellWidget(row, save_col)
        if isinstance(btn, QPushButton):
            btn.setText("✅" if is_saved else "❓")

    def save_row_to_db(self, row):
        if self.signalsBlocked() or row < 0 or row >= self.rowCount(): return
        
        sorting_was_enabled = self.isSortingEnabled()
        self.setSortingEnabled(False)
        
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
            
            if entry_id:
                update_ledger_entry(entry_id, date, self.entry_type, cat_id, asset_id, amount, memo, payee, pay_method)
            else:
                if date:
                    new_id = add_ledger_entry(self.ledger_tab.hid, date, self.entry_type, cat_id, asset_id, amount, memo, payee, pay_method)
                    if new_id:
                        self.blockSignals(True)
                        self.setItem(row, 0, QTableWidgetItem(str(new_id)))
                        self.blockSignals(False)
            
            self.set_save_status(row, True)
            self.ledger_tab.refresh_summary()
        except Exception as e:
            print(f"DEBUG Save error: {e}")
        finally:
            self.setSortingEnabled(sorting_was_enabled)

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
    def __init__(self, hid=None, month=1):
        super().__init__()
        self.hid = hid
        self.month = month
        self.year = 2026
        self.category_color_map = {}
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        self.summary_label = QLabel("월 예산: 0 | 지출: 0 | 남은 예산: 0")
        self.summary_label.setObjectName("SummaryLabel")
        layout.addWidget(self.summary_label)

        content_layout = QHBoxLayout()
        exp_columns = ["소비날짜", "결제수단", "수단명", "대분류", "항목", "지출금액", "사용처", "코멘트"]
        self.expense_box = self.create_section("💸 소비 내역 (지출)", "지출", exp_columns)
        inc_columns = ["소득날짜", "대분류", "항목", "소득 금액", "소득처"]
        self.income_box = self.create_section("💰 소득 내역 (수입)", "수입", inc_columns)

        content_layout.addWidget(self.expense_box, 3)
        content_layout.addWidget(self.income_box, 2)
        layout.addLayout(content_layout)

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
        
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addStretch()
        
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

    def refresh_data(self):
        if self.hid is None: return
        self.refresh_category_colors()
        self.income_table.setSortingEnabled(False)
        self.expense_table.setSortingEnabled(False)
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
        self.income_table.setSortingEnabled(True)
        self.expense_table.setSortingEnabled(True)
        self.refresh_summary()

    def refresh_category_colors(self):
        self.category_color_map = {}
        for db_type in ["소비", "소득"]:
            for category in get_categories(self.hid, db_type):
                if len(category) > 4 and category[4]:
                    self.category_color_map[(category[1], category[2], category[3])] = category[4]

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
                else:
                    widget.setStyleSheet("")
            elif isinstance(widget, QPushButton) and widget.objectName() == "SaveBtn":
                if bg_color and bg_color.isValid():
                    text = text_color.name() if text_color else "#202124"
                    widget.setStyleSheet(f"background-color: {color}; color: {text};")
                else:
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
        elif col == amt_col:
            table.setItem(row, col, NumericTableWidgetItem(val or "0"))
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
            from database import get_categories
            if ctype == "수단명":
                items = [c[3] for c in get_categories(self.hid, "결제수단") if c[2] == parent_val]
            elif ctype == "소비_중":
                items = [c[3] for c in get_categories(self.hid, "소비") if c[2] == parent_val]
            elif ctype == "소득_중":
                items = [c[3] for c in get_categories(self.hid, "소득") if c[2] == parent_val]
            else:
                items = []
            child_combo.addItems(items)
            child_combo.setCurrentIndex(-1)
            child_item = table.item(row, child_col)
            if child_item: child_item.setText("")
            child_combo.blockSignals(False)

    def populate_combo(self, combo, ctype, table, row, col):
        from database import get_categories
        if ctype == "결제수단":
            items = sorted(list(set(c[2] for c in get_categories(self.hid, "결제수단"))))
        elif ctype == "수단명":
            p = table.get_val(row, 2)
            items = [c[3] for c in get_categories(self.hid, "결제수단") if c[2] == p]
        elif ctype == "소비_대":
            items = sorted(list(set(c[2] for c in get_categories(self.hid, "소비"))))
        elif ctype == "소비_중":
            p = table.get_val(row, 4)
            items = [c[3] for c in get_categories(self.hid, "소비") if c[2] == p]
        elif ctype == "소득_대":
            items = sorted(list(set(c[2] for c in get_categories(self.hid, "소득"))))
        elif ctype == "소득_중":
            p = table.get_val(row, 2)
            items = [c[3] for c in get_categories(self.hid, "소득") if c[2] == p]
        else:
            items = []
        combo.addItems(items)

    def add_row(self, table):
        table.setSortingEnabled(False)
        table.blockSignals(True)
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(""))
        table.setItem(row, 1, QTableWidgetItem(f"{self.year}-{self.month:02d}-01"))
        for col in range(2, table.columnCount() - 1):
            dv = "0" if (table.entry_type=="지출" and col==6) or (table.entry_type=="수입" and col==4) else ""
            self.set_table_item(table, row, col, dv)
        self.add_save_button(table, row, False)
        table.scrollToBottom()
        table.blockSignals(False)
        table.setSortingEnabled(True)

    def delete_row(self, table):
        row = table.currentRow()
        if row < 0: return
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
        def sum_table(table, col):
            total = 0
            for r in range(table.rowCount()):
                if not table.isRowHidden(r):
                    total += table.get_int(r, col)
            return total
        exp = sum_table(self.expense_table, 6)
        remaining = monthly_total_budget - exp
        self.summary_label.setText(f"월 예산: {monthly_total_budget:,} | 지출: {exp:,} | 남은 예산: {remaining:,}")

    def resolve_category_id(self, etype, p, s):
        db_type = "소비" if etype == "지출" else "소득"
        from database import get_categories
        for c in get_categories(self.hid, db_type):
            if c[2] == p and c[3] == s: return c[0]
        return None

    def resolve_asset_id(self, etype, pm, an):
        from database import get_categories
        if etype == "지출":
            for c in get_categories(self.hid, "결제수단"):
                if c[2] == pm and c[3] == an: return c[0]
        return None
