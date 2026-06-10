import openpyxl
from database import (add_category, save_detailed_budget, add_asset, 
                      add_ledger_entry, clear_all_data, get_db_connection)
from PyQt6.QtWidgets import QMessageBox

def import_from_excel(file_path, parent_widget):
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        
        # 1. Ask for confirmation
        reply = QMessageBox.question(
            parent_widget, "데이터 이관 확인",
            "기존 모든 데이터를 삭제하고 엑셀 데이터를 가져오시겠습니까?\n(가져오기 후 프로그램이 최신 상태로 갱신됩니다.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return False

        # Clear existing data
        clear_all_data()

        # 2. Parse '설정하기' (Categories)
        if '설정하기' in wb.sheetnames:
            sheet = wb['설정하기']
            current_type = "소비" # Default
            for row in sheet.iter_rows(min_row=1, values_only=True):
                if not row[0]: continue
                header = str(row[0])
                if "소비 분류" in header: current_type = "소비"
                elif "소득 분류" in header: current_type = "소득"
                elif "결제수단" in header: current_type = "결제수단"
                elif "자본" in header or "부채" in header: current_type = "자본"
                
                # If it's a category row (Parent in A, Subs in C onwards)
                if row[2]: # Has subcategories in Col C
                    parent = row[0]
                    for col_idx in range(2, len(row)):
                        sub = row[col_idx]
                        if sub:
                            add_category(current_type, parent, sub)

        # 3. Parse '예산 설정'
        if '예산 설정' in wb.sheetnames:
            sheet = wb['예산 설정']
            # Header is row 1, months start row 3
            headers = [cell for cell in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True)) if cell]
            # headers[2:] are category names
            for row in sheet.iter_rows(min_row=3, values_only=True):
                month_str = str(row[1]) if row[1] else ""
                if "월" in month_str:
                    month = int(month_str.replace("월", ""))
                    for i, amt in enumerate(row[2:]):
                        if i + 2 < len(headers) and amt:
                            cat_name = headers[i+2]
                            save_detailed_budget(2026, month, cat_name, int(amt))

        # 4. Parse '자산 관리' (Initial Assets)
        if '자산 관리' in wb.sheetnames:
            sheet = wb['자산 관리']
            # Based on sample, assets might be in a specific range. 
            # We'll just add '자본금' as a default if found
            for row in sheet.iter_rows(min_row=1, values_only=True):
                if row[1] == "자본금" and row[2]:
                    add_asset("자본금", int(row[2]))

        # 5. Parse Monthly Ledger (1월 ~ 12월)
        # We need a quick lookup for category/asset IDs
        cat_map = {} # (type, parent, sub) -> id
        def refresh_cat_map():
            nonlocal cat_map
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, type, parent_category, sub_category FROM categories")
            for r in cursor.fetchall():
                cat_map[(r[1], r[2], r[3])] = r[0]
            conn.close()
        
        refresh_cat_map()

        for month in range(1, 13):
            sheet_name = f"{month}월"
            if sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                # Expense (A-H), Income (J-O)
                # Row 1-3 is headers, data starts row 4
                for row in sheet.iter_rows(min_row=4, values_only=True):
                    # --- Expense (지출) ---
                    if row[0] and row[5]: # Date and Amount
                        date_val = row[0]
                        if isinstance(date_val, str): date_str = date_val
                        else: date_str = date_val.strftime("%Y-%m-%d")
                        
                        pay_method = str(row[1]) if row[1] else ""
                        asset_name = str(row[2]) if row[2] else ""
                        parent = str(row[3]) if row[3] else ""
                        sub = str(row[4]) if row[4] else ""
                        amount = int(row[5])
                        payee = str(row[6]) if row[6] else ""
                        memo = str(row[7]) if row[7] else ""
                        
                        cat_id = cat_map.get(("소비", parent, sub))
                        asset_id = cat_map.get(("결제수단", pay_method, asset_name))
                        
                        add_ledger_entry(date_str, "지출", cat_id, asset_id, amount, memo, payee, pay_method)

                    # --- Income (수입) ---
                    if row[9] and row[12]: # Income Date and Amount (Col J and M)
                        date_val = row[9]
                        if isinstance(date_val, str): date_str = date_val
                        else: date_str = date_val.strftime("%Y-%m-%d")
                        
                        parent = str(row[10]) if row[10] else ""
                        sub = str(row[11]) if row[11] else ""
                        amount = int(row[12])
                        payee = str(row[13]) if row[13] else ""
                        memo = str(row[14]) if row[14] else ""
                        
                        cat_id = cat_map.get(("소득", parent, sub))
                        add_ledger_entry(date_str, "수입", cat_id, None, amount, memo, payee, "")

        QMessageBox.information(parent_widget, "완료", "엑셀 데이터 이관이 성공적으로 완료되었습니다.")
        return True

    except Exception as e:
        QMessageBox.critical(parent_widget, "오류", f"엑셀 임포트 중 오류 발생: {e}")
        return False
