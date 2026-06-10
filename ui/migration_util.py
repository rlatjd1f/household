import openpyxl
import re
from datetime import date, datetime
from database import (add_category, save_detailed_budget, add_asset, 
                      add_ledger_entry, clear_household_data, get_db_connection)
from PyQt6.QtWidgets import QMessageBox

def to_int(value):
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None

def parse_excel_date(value, year, fallback_month=None):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    text = str(value).strip()
    if not text:
        return None

    iso_match = re.search(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", text)
    if iso_match:
        y, m, d = map(int, iso_match.groups())
        return f"{y:04d}-{m:02d}-{d:02d}"

    month_day_match = re.search(r"(\d{1,2})\s*[./]\s*(\d{1,2})", text)
    if month_day_match:
        m, d = map(int, month_day_match.groups())
        return f"{year:04d}-{m:02d}-{d:02d}"

    day_match = re.fullmatch(r"\d{1,2}", text)
    if day_match and fallback_month:
        return f"{year:04d}-{fallback_month:02d}-{int(text):02d}"

    return text

def get_import_year(wb):
    if "설정하기" not in wb.sheetnames:
        return datetime.now().year

    sheet = wb["설정하기"]
    for row in sheet.iter_rows(values_only=True):
        for idx, value in enumerate(row):
            if value == "연도 설정":
                for next_value in row[idx + 1:]:
                    year = to_int(next_value)
                    if year:
                        return year
    return datetime.now().year

def find_header_row(sheet):
    for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        values = [str(value).strip() if value is not None else "" for value in row]
        if "소비날짜" in values and "소득날짜" in values:
            return row_idx, values
    return None, []

def import_from_excel(hid, file_path, parent_widget):
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        import_year = get_import_year(wb)
        
        reply = QMessageBox.question(
            parent_widget, "데이터 이관 확인",
            "기존 모든 데이터를 삭제하고 엑셀 데이터를 가져오시겠습니까?\n(가져오기 후 프로그램이 최신 상태로 갱신됩니다.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No: return False

        # Clear data for THIS household only
        clear_household_data(hid)

        # 2. Categories
        if '설정하기' in wb.sheetnames:
            sheet = wb['설정하기']
            current_type = "소비"
            for row in sheet.iter_rows(min_row=1, values_only=True):
                if not row[0]: continue
                h = str(row[0]).strip()
                if "소비 분류" in h: current_type = "소비"
                elif "소득 분류" in h: current_type = "소득"
                elif "결제분류" in h: current_type = "결제수단"
                elif "자본" in h and "부채" in h: current_type = "자본"
                if row[2]:
                    parent = row[0]
                    if parent in ["연도 설정", "소비 분류", "결제분류", "소득 분류", "자본, 부채 분류"]: continue
                    for col_idx in range(2, len(row)):
                        sub = row[col_idx]
                        if sub: add_category(hid, current_type, parent, sub)

        # 3. Budget
        if '예산 설정' in wb.sheetnames:
            sheet = wb['예산 설정']
            headers = [c for c in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True)) if c]
            for row in sheet.iter_rows(min_row=3, values_only=True):
                ms = str(row[1]) if row[1] else ""
                if "월" in ms:
                    month = int(ms.replace("월", ""))
                    for i, amt in enumerate(row[2:]):
                        if i + 2 < len(headers) and amt:
                            save_detailed_budget(hid, import_year, month, headers[i+2], int(amt))

        # 4. Assets
        if '자산 관리' in wb.sheetnames:
            sheet = wb['자산 관리']
            for row in sheet.iter_rows(min_row=1, values_only=True):
                values = list(row)
                for idx, value in enumerate(values):
                    if value == "자본금":
                        for next_value in values[idx + 1:]:
                            amount = to_int(next_value)
                            if amount is not None:
                                add_asset(hid, "자본금", amount)
                                break
                        break

        # 5. Ledger
        cat_map = {}
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, type, parent_category, sub_category FROM categories WHERE household_id = ?", (hid,))
        for r in cursor.fetchall(): cat_map[(r[1], r[2], r[3])] = r[0]
        conn.close()

        for month in range(1, 13):
            sheet_name = f"{month}월"
            if sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                header_row, headers = find_header_row(sheet)
                if not header_row:
                    continue
                expense_start = headers.index("소비날짜")
                income_start = headers.index("소득날짜")

                for row in sheet.iter_rows(min_row=header_row + 1, values_only=True):
                    expense_amount = to_int(row[expense_start + 5] if len(row) > expense_start + 5 else None)
                    if len(row) > expense_start and row[expense_start] and expense_amount:
                        ds = parse_excel_date(row[expense_start], import_year, month)
                        pm = str(row[expense_start + 1]).strip() if len(row) > expense_start + 1 and row[expense_start + 1] else ""
                        an = str(row[expense_start + 2]).strip() if len(row) > expense_start + 2 and row[expense_start + 2] else ""
                        p = str(row[expense_start + 3]).strip() if len(row) > expense_start + 3 and row[expense_start + 3] else ""
                        s = str(row[expense_start + 4]).strip() if len(row) > expense_start + 4 and row[expense_start + 4] else ""
                        payee = str(row[expense_start + 6]).strip() if len(row) > expense_start + 6 and row[expense_start + 6] else ""
                        memo = str(row[expense_start + 7]).strip() if len(row) > expense_start + 7 and row[expense_start + 7] else ""
                        cat_id = cat_map.get(("소비", p, s))
                        asset_id = cat_map.get(("결제수단", pm, an))
                        add_ledger_entry(hid, ds, "지출", cat_id, asset_id, expense_amount, memo, payee, pm)

                    income_amount = to_int(row[income_start + 3] if len(row) > income_start + 3 else None)
                    if len(row) > income_start and row[income_start] and income_amount:
                        ds = parse_excel_date(row[income_start], import_year, month)
                        p = str(row[income_start + 1]).strip() if len(row) > income_start + 1 and row[income_start + 1] else ""
                        s = str(row[income_start + 2]).strip() if len(row) > income_start + 2 and row[income_start + 2] else ""
                        payee = str(row[income_start + 4]).strip() if len(row) > income_start + 4 and row[income_start + 4] else ""
                        memo = str(row[income_start + 5]).strip() if len(row) > income_start + 5 and row[income_start + 5] else ""
                        cat_id = cat_map.get(("소득", p, s))
                        add_ledger_entry(hid, ds, "수입", cat_id, None, income_amount, memo, payee, "")

        QMessageBox.information(parent_widget, "완료", "엑셀 데이터 이관이 성공적으로 완료되었습니다.")
        return True
    except Exception as e:
        QMessageBox.critical(parent_widget, "오류", f"엑셀 임포트 중 오류 발생: {e}"); return False
