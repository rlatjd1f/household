import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / "household_test.db"
os.environ["HOUSEHOLD_DB_PATH"] = str(TEST_DB)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database


def reset_db():
    if TEST_DB.exists():
        TEST_DB.unlink()
    database.init_db()
    return database.get_households()[0][0]


def count_rows(table, hid):
    conn = sqlite3.connect(database.DB_NAME)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE household_id = ?", (hid,)).fetchone()[0]
    finally:
        conn.close()


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.hid = reset_db()

    def test_uses_override_path(self):
        self.assertEqual(Path(database.DB_NAME), TEST_DB)

    def test_ledger_entry_does_not_touch_asset_balance(self):
        database.add_asset(self.hid, "자본금", 1000)
        database.add_category(self.hid, "결제수단", "카드", "국민카드")
        payment_id = database.get_categories(self.hid, "결제수단")[0][0]
        asset_id = database.get_assets(self.hid)[0][0]
        self.assertEqual(payment_id, asset_id)  # 같은 id여도 자산 잔액이 바뀌면 안 됨

        entry_id = database.add_ledger_entry(self.hid, "2026-01-02", "지출", None, payment_id, 300, "", "", "카드")
        database.update_ledger_entry(entry_id, "2026-01-02", "지출", None, payment_id, 500, "", "", "카드")
        database.delete_ledger_entry(entry_id)
        self.assertEqual(database.get_assets(self.hid)[0][3], 1000)

    def test_delete_household_removes_child_rows(self):
        hid = database.add_household("삭제용")
        database.add_category(hid, "소비", "식비", "외식")
        database.add_asset(hid, "통장", 10)
        database.save_detailed_budget(hid, 2026, 1, "식비", 100)
        database.add_ledger_entry(hid, "2026-01-01", "지출", None, None, 10, "", "", "")
        database.delete_household(hid)
        for table in ("categories", "assets", "budgets", "ledgers"):
            self.assertEqual(count_rows(table, hid), 0, table)

    def test_data_migration_cleans_orphans_and_resets_balance(self):
        database.add_asset(self.hid, "자본금", 1000)
        conn = sqlite3.connect(database.DB_NAME)
        conn.execute("UPDATE assets SET current_balance = 1")
        conn.execute("INSERT INTO categories (household_id, type, parent_category, sub_category) VALUES (999, '소비', 'a', 'b')")
        conn.execute("PRAGMA user_version = 0")
        conn.commit()
        conn.close()

        database.init_db()
        self.assertEqual(database.get_assets(self.hid)[0][3], 1000)
        self.assertEqual(count_rows("categories", 999), 0)

    def test_rebuild_table_keeps_rows(self):
        conn = sqlite3.connect(database.DB_NAME)
        conn.execute("DROP TABLE assets")
        conn.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY, household_id INTEGER, asset_name TEXT UNIQUE, initial_balance INTEGER, current_balance INTEGER)")
        conn.execute("INSERT INTO assets (household_id, asset_name, initial_balance, current_balance) VALUES (?, '통장', 50, 50)", (self.hid,))
        conn.commit()
        conn.close()

        database.init_db()
        self.assertEqual([row[1:] for row in database.get_assets(self.hid)], [("통장", 50, 50)])
        conn = sqlite3.connect(database.DB_NAME)
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'assets'").fetchone()[0]
        conn.close()
        self.assertIn("UNIQUE(household_id,", sql.replace(" ", ""))

    def test_save_detailed_budgets(self):
        database.save_detailed_budgets(self.hid, 2026, [(1, "식비", 100), (2, "식비", 200)])
        database.save_detailed_budgets(self.hid, 2026, [(1, "식비", 150)])
        self.assertEqual(database.get_detailed_budgets(self.hid, 2026), {"식비": {1: 150, 2: 200}})

    def test_import_household_year_replaces_only_that_year(self):
        database.add_category(self.hid, "소비", "식비", "외식")
        database.add_ledger_entry(self.hid, "2025-05-01", "지출", None, None, 1, "", "", "")
        database.add_ledger_entry(self.hid, "2026-05-01", "지출", None, None, 2, "", "", "")
        old_cat_id = database.get_categories(self.hid, "소비")[0][0]

        database.import_household_year(
            self.hid, 2026,
            categories=[("소비", "식비", "외식"), ("결제수단", "카드", "국민카드")],
            budgets=[(1, "식비", 100)],
            assets=[("자본금", 500)],
            ledgers=[{"date": "2026-03-01", "type": "지출", "category": ("소비", "식비", "외식"),
                      "payment": ("결제수단", "카드", "국민카드"), "amount": 9000,
                      "memo": "", "payee": "식당", "payment_method": "카드"}],
        )
        self.assertEqual(database.get_categories(self.hid, "소비")[0][0], old_cat_id)
        self.assertEqual(len(database.get_ledger_entries(self.hid, 2025, 5)), 1)
        self.assertEqual(database.get_ledger_entries(self.hid, 2026, 5), [])
        march = database.get_ledger_entries(self.hid, 2026, 3)
        self.assertEqual((march[0][5], march[0][9], march[0][11]), (9000, "식비", "국민카드"))

    def test_import_household_year_rolls_back_on_error(self):
        database.add_ledger_entry(self.hid, "2026-05-01", "지출", None, None, 2, "", "", "")
        with self.assertRaises(Exception):
            database.import_household_year(self.hid, 2026, [], [], [], [{"date": None, "type": "지출"}])
        self.assertEqual(len(database.get_ledger_entries(self.hid, 2026, 5)), 1)


if __name__ == "__main__":
    unittest.main()
