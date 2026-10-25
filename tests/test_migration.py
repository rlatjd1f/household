import os
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / "household_test.db"
os.environ["HOUSEHOLD_DB_PATH"] = str(TEST_DB)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openpyxl
import database
from ui.migration_util import build_export_workbook, parse_workbook


class ExcelRoundTripTest(unittest.TestCase):
    def setUp(self):
        if TEST_DB.exists():
            TEST_DB.unlink()
        database.init_db()
        self.hid = database.get_households()[0][0]

    def test_export_then_import_round_trip(self):
        hid = self.hid
        database.add_category(hid, "소비", "식비", "외식")
        database.add_category(hid, "소득", "급여", "월급")
        database.add_category(hid, "결제수단", "카드", "국민카드")
        database.add_asset(hid, "자본금", 1000000)
        database.save_detailed_budgets(hid, 2026, [(m, "식비", 300000) for m in range(1, 13)])
        cats = {(c[1], c[2], c[3]): c[0] for c in database.get_categories(hid)}
        database.add_ledger_entry(hid, "2026-03-05", "지출", cats[("소비", "식비", "외식")],
                                  cats[("결제수단", "카드", "국민카드")], 12000, "점심", "식당", "카드")
        database.add_ledger_entry(hid, "2026-03-25", "수입", cats[("소득", "급여", "월급")],
                                  None, 3000000, "", "회사", "")

        path = Path(tempfile.gettempdir()) / "household_roundtrip.xlsx"
        build_export_workbook(hid, 2026).save(path)
        year, categories, budgets, assets, ledgers = parse_workbook(openpyxl.load_workbook(path, data_only=True))

        self.assertEqual(year, 2026)
        self.assertIn(("결제수단", "카드", "국민카드"), categories)
        self.assertEqual(len(budgets), 12)
        self.assertEqual(assets, [("자본금", 1000000)])
        self.assertEqual(len(ledgers), 2)

        target = database.add_household("이관 대상")
        database.import_household_year(target, year, categories, budgets, assets, ledgers)
        march = database.get_ledger_entries(target, 2026, 3)
        expense = [e for e in march if e[2] == "지출"][0]
        income = [e for e in march if e[2] == "수입"][0]
        self.assertEqual((expense[1], expense[5], expense[9], expense[10], expense[11], expense[7]),
                         ("2026-03-05", 12000, "식비", "외식", "국민카드", "식당"))
        self.assertEqual((income[5], income[9], income[10]), (3000000, "급여", "월급"))
        self.assertEqual(database.get_detailed_budgets(target, 2026)["식비"][7], 300000)


if __name__ == "__main__":
    unittest.main()
