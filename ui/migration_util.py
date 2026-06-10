import openpyxl
from database import (add_category, save_detailed_budget, add_asset, 
                      add_ledger_entry, clear_household_data, get_db_connection)
from PyQt6.QtWidgets import QMessageBox

def import_from_excel(hid, file_path, parent_widget):
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        
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
                            save_detailed_budget(hid, 2026, month, headers[i+2], int(amt))

        # 4. Assets
        if '자산 관리' in wb.sheetnames:
            sheet = wb['자산 관리']
            for row in sheet.iter_rows(min_row=1, values_only=True):
                if row[1] == "자본금" and row[2]: add_asset(hid, "자본금", int(row[2]))

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
                for row in sheet.iter_rows(min_row=4, values_only=True):
                    if row[0] and row[5]:
                        dv = row[0]; ds = dv if isinstance(dv, str) else dv.strftime("%Y-%m-%d")
                        pm = str(row[1]) if row[1] else ""; an = str(row[2]) if row[2] else ""
                        p = str(row[3]) if row[3] else ""; s = str(row[4]) if row[4] else ""
                        cat_id = cat_map.get(("소비", p, s))
                        asset_id = cat_map.get(("결제수단", pm, an))
                        add_ledger_entry(hid, ds, "지출", cat_id, asset_id, int(row[5]), str(row[7]) if row[7] else "", str(row[6]) if row[6] else "", pm)
                    if row[9] and row[12]:
                        dv = row[9]; ds = dv if isinstance(dv, str) else dv.strftime("%Y-%m-%d")
                        p = str(row[10]) if row[10] else ""; s = str(row[11]) if row[11] else ""
                        cat_id = cat_map.get(("소득", p, s))
                        add_ledger_entry(hid, ds, "수입", cat_id, None, str(row[14]) if row[14] else "", str(row[13]) if row[13] else "", "")

        QMessageBox.information(parent_widget, "완료", "엑셀 데이터 이관이 성공적으로 완료되었습니다.")
        return True
    except Exception as e:
        QMessageBox.critical(parent_widget, "오류", f"엑셀 임포트 중 오류 발생: {e}"); return False
