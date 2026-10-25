import sqlite3
import os
import shutil
import sys
from pathlib import Path

APP_NAME = "HouseholdManager"
DB_FILENAME = "household.db"
LEGACY_DB_PATH = Path(DB_FILENAME).resolve()


def get_app_data_dir():
    if sys.platform == "win32":
        base_dir = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base_dir) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME


def get_db_path():
    # HOUSEHOLD_DB_PATH: 테스트 등에서 별도 DB 파일을 쓰기 위한 경로 지정
    override = os.environ.get("HOUSEHOLD_DB_PATH")
    if override:
        return Path(override)
    return get_app_data_dir() / DB_FILENAME


DB_NAME = str(get_db_path())
DB_DEBUG = bool(os.environ.get("HOUSEHOLD_DB_DEBUG"))
SCHEMA_VERSION = 1


def migrate_legacy_db():
    target_path = get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if os.environ.get("HOUSEHOLD_DB_PATH"):
        return
    if target_path.exists() or not LEGACY_DB_PATH.exists():
        return
    if LEGACY_DB_PATH == target_path:
        return
    shutil.copy2(LEGACY_DB_PATH, target_path)

def init_db():
    migrate_legacy_db()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 0. Households Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS households (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 1. Categories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id INTEGER NOT NULL,
        type TEXT NOT NULL, 
        parent_category TEXT NOT NULL, 
        sub_category TEXT NOT NULL, 
        color TEXT,
        UNIQUE(household_id, type, parent_category, sub_category),
        FOREIGN KEY (household_id) REFERENCES households (id) ON DELETE CASCADE
    )
    """)

    # 2. Budgets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        category_name TEXT NOT NULL,
        amount INTEGER DEFAULT 0,
        UNIQUE(household_id, year, month, category_name),
        FOREIGN KEY (household_id) REFERENCES households (id) ON DELETE CASCADE
    )
    """)

    # 3. Assets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id INTEGER NOT NULL,
        asset_name TEXT NOT NULL,
        initial_balance INTEGER DEFAULT 0,
        current_balance INTEGER DEFAULT 0,
        UNIQUE(household_id, asset_name),
        FOREIGN KEY (household_id) REFERENCES households (id) ON DELETE CASCADE
    )
    """)

    # 4. Ledgers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledgers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id INTEGER NOT NULL,
        date TEXT NOT NULL, 
        type TEXT NOT NULL, 
        category_id INTEGER,
        asset_id INTEGER,
        amount INTEGER NOT NULL,
        memo TEXT,
        payee TEXT,
        payment_method TEXT,
        FOREIGN KEY (household_id) REFERENCES households (id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (asset_id) REFERENCES assets (id)
    )
    """)

    conn.commit()

    # --- Migration Logic: Force Recreate if UNIQUE constraint is broken ---
    tables_to_repair = {
        "categories": """
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER NOT NULL,
                type TEXT NOT NULL, 
                parent_category TEXT NOT NULL, 
                sub_category TEXT NOT NULL, 
                color TEXT,
                UNIQUE(household_id, type, parent_category, sub_category),
                FOREIGN KEY (household_id) REFERENCES households (id) ON DELETE CASCADE
            )""",
        "budgets": """
            CREATE TABLE budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                category_name TEXT NOT NULL,
                amount INTEGER DEFAULT 0,
                UNIQUE(household_id, year, month, category_name),
                FOREIGN KEY (household_id) REFERENCES households (id) ON DELETE CASCADE
            )""",
        "assets": """
            CREATE TABLE assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER NOT NULL,
                asset_name TEXT NOT NULL,
                initial_balance INTEGER DEFAULT 0,
                current_balance INTEGER DEFAULT 0,
                UNIQUE(household_id, asset_name),
                FOREIGN KEY (household_id) REFERENCES households (id) ON DELETE CASCADE
            )"""
    }

    # Ensure at least one household exists
    cursor.execute("SELECT count(*) FROM households")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO households (name) VALUES ('기본 가계부')")
        conn.commit()
    
    cursor.execute("SELECT id FROM households LIMIT 1")
    default_hid = cursor.fetchone()[0]

    for table, create_sql in tables_to_repair.items():
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
        table_sql = cursor.fetchone()
        
        if table_sql:
            sql_str = table_sql[0].replace(' ', '').replace('\n', '')
            # Robust check for the proper UNIQUE constraint including household_id
            if f"UNIQUE(household_id," not in sql_str:
                print(f"Repairing {table}: UNIQUE constraint missing household_id. Rebuilding...")
                rebuild_table(cursor, table, create_sql, default_hid)
                conn.commit()

    # Ledgers migration (Individual columns)
    cursor.execute(f"PRAGMA table_info(categories)")
    c_cols = [row[1] for row in cursor.fetchall()]
    if "color" not in c_cols:
        cursor.execute("ALTER TABLE categories ADD COLUMN color TEXT")

    cursor.execute(f"PRAGMA table_info(ledgers)")
    l_cols = [row[1] for row in cursor.fetchall()]
    if "household_id" not in l_cols:
        cursor.execute(f"ALTER TABLE ledgers ADD COLUMN household_id INTEGER REFERENCES households(id)")
        cursor.execute(f"UPDATE ledgers SET household_id = ?", (default_hid,))
    if "payee" not in l_cols: cursor.execute("ALTER TABLE ledgers ADD COLUMN payee TEXT")
    if "payment_method" not in l_cols: cursor.execute("ALTER TABLE ledgers ADD COLUMN payment_method TEXT")

    conn.commit()
    apply_data_migrations(conn)
    conn.close()
    print(f"Database {DB_NAME} initialized correctly.")

def rebuild_table(cursor, table, create_sql, default_hid):
    """Recreate a table with the current schema while keeping its rows."""
    temp_table = f"{table}_rebuild"
    cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
    cursor.execute(create_sql.replace(f"CREATE TABLE {table}", f"CREATE TABLE {temp_table}", 1))
    cursor.execute(f"PRAGMA table_info({table})")
    old_cols = {row[1] for row in cursor.fetchall()}
    cursor.execute(f"PRAGMA table_info({temp_table})")
    new_cols = [row[1] for row in cursor.fetchall()]
    select_exprs = []
    for col in new_cols:
        if col in old_cols: select_exprs.append(col)
        elif col == "household_id": select_exprs.append(str(int(default_hid)))
        else: select_exprs.append("NULL")
    cursor.execute(f"INSERT OR IGNORE INTO {temp_table} ({', '.join(new_cols)}) SELECT {', '.join(select_exprs)} FROM {table}")
    cursor.execute(f"DROP TABLE {table}")
    cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table}")

def apply_data_migrations(conn):
    cursor = conn.cursor()
    version = cursor.execute("PRAGMA user_version").fetchone()[0]
    if version < 1:
        # 가계부 내역의 asset_id는 결제수단 분류(categories.id)를 가리키는데,
        # 이전 버전은 같은 id로 assets 잔액을 갱신해 엉뚱한 자산 잔액이 바뀌었음.
        cursor.execute("UPDATE assets SET current_balance = initial_balance")
        # 외래키가 꺼져 있어 가계부 삭제 시 남은 데이터 정리
        for table in ("categories", "budgets", "assets", "ledgers"):
            cursor.execute(f"DELETE FROM {table} WHERE household_id IS NULL OR household_id NOT IN (SELECT id FROM households)")
    if version < SCHEMA_VERSION:
        cursor.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()

def get_db_connection():
    get_db_path().parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_NAME)

def log_query(query, params=None):
    if not DB_DEBUG: return
    print(f"\n[DB LOG] {query.strip()}")
    if params: print(f"        {params}")

# --- Household Management Functions ---
def add_household(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO households (name) VALUES (?)", (name,))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_households():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM households ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_household(hid):
    # foreign_keys가 꺼져 있어 ON DELETE CASCADE가 동작하지 않으므로 직접 삭제
    conn = get_db_connection()
    try:
        with conn:
            _delete_household_rows(conn.cursor(), hid)
            conn.execute("DELETE FROM households WHERE id = ?", (hid,))
    finally:
        conn.close()

def _delete_household_rows(cursor, hid):
    for table in ("ledgers", "budgets", "assets", "categories"):
        cursor.execute(f"DELETE FROM {table} WHERE household_id = ?", (hid,))

def update_household_name(hid, new_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE households SET name = ? WHERE id = ?", (new_name, hid))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# --- Category Functions ---
def add_category(hid, category_type, parent, sub):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "INSERT INTO categories (household_id, type, parent_category, sub_category, color) VALUES (?, ?, ?, ?, NULL)"
    params = (hid, category_type, parent, sub)
    log_query(query, params)
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_categories(hid, category_type=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if category_type:
        query = "SELECT id, type, parent_category, sub_category, color FROM categories WHERE household_id = ? AND type = ?"
        params = (hid, category_type)
    else:
        query = "SELECT id, type, parent_category, sub_category, color FROM categories WHERE household_id = ?"
        params = (hid,)
    log_query(query, params)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "DELETE FROM categories WHERE id = ?"
    log_query(query, (category_id,))
    cursor.execute(query, (category_id,))
    conn.commit()
    conn.close()

def delete_category_by_parent(hid, db_type, parent_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "DELETE FROM categories WHERE household_id = ? AND type = ? AND parent_category = ?"
    params = (hid, db_type, parent_name)
    log_query(query, params)
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def update_category_parent_name(hid, db_type, old_name, new_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "UPDATE categories SET parent_category = ? WHERE household_id = ? AND type = ? AND parent_category = ?"
    params = (new_name, hid, db_type, old_name)
    log_query(query, params)
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def update_category_sub_name(cat_id, new_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "UPDATE categories SET sub_category = ? WHERE id = ?"
    params = (new_name, cat_id)
    log_query(query, params)
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def update_category_color(cat_id, color):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "UPDATE categories SET color = ? WHERE id = ?"
    params = (color, cat_id)
    log_query(query, params)
    cursor.execute(query, params)
    conn.commit()
    conn.close()

# --- Asset Functions ---
def add_asset(hid, name, initial_balance):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "INSERT INTO assets (household_id, asset_name, initial_balance, current_balance) VALUES (?, ?, ?, ?)"
    params = (hid, name, initial_balance, initial_balance)
    log_query(query, params)
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_assets(hid):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT id, asset_name, initial_balance, current_balance FROM assets WHERE household_id = ?"
    log_query(query, (hid,))
    cursor.execute(query, (hid,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_asset(asset_id, name, initial_balance):
    """자산명과 기초 잔액 수정. 이름이 겹치면 False"""
    conn = get_db_connection()
    try:
        with conn:
            # 현재 잔액은 기초 잔액에서 바뀐 만큼 함께 조정
            conn.execute(
                "UPDATE assets SET asset_name = ?, current_balance = current_balance + (? - initial_balance), initial_balance = ? WHERE id = ?",
                (name, initial_balance, initial_balance, asset_id)
            )
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_asset(asset_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "DELETE FROM assets WHERE id = ?"
    log_query(query, (asset_id,))
    cursor.execute(query, (asset_id,))
    conn.commit()
    conn.close()

# --- Ledger Functions ---
def add_ledger_entry(hid, date, entry_type, category_id, asset_id, amount, memo, payee, payment_method):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "INSERT INTO ledgers (household_id, date, type, category_id, asset_id, amount, memo, payee, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        params = (hid, date, entry_type, category_id, asset_id, amount, memo, payee, payment_method)
        log_query(query, params)
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error adding ledger: {e}")
        return None
    finally:
        conn.close()

def update_ledger_entry(entry_id, date, entry_type, category_id, asset_id, amount, memo, payee, payment_method):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "UPDATE ledgers SET date=?, type=?, category_id=?, asset_id=?, amount=?, memo=?, payee=?, payment_method=? WHERE id=?"
        params = (date, entry_type, category_id, asset_id, amount, memo, payee, payment_method, entry_id)
        log_query(query, params)
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating ledger: {e}")
        return False
    finally:
        conn.close()

def get_ledger_entries(hid, year, month):
    conn = get_db_connection()
    cursor = conn.cursor()
    month_str = f"{month:02d}"
    query = """
        SELECT l.id, l.date, l.type, l.category_id, l.asset_id, l.amount, l.memo, l.payee, l.payment_method,
               c.parent_category, c.sub_category, p.sub_category as asset_name, c.color
        FROM ledgers l
        LEFT JOIN categories c ON l.category_id = c.id
        LEFT JOIN categories p ON l.asset_id = p.id
        WHERE l.household_id = ? AND l.date LIKE ?
        ORDER BY l.date ASC, l.id ASC
    """
    params = (hid, f"{year}-{month_str}-%")
    log_query(query, params)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_ledger_entry(entry_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "DELETE FROM ledgers WHERE id = ?"
    log_query(query, (entry_id,))
    cursor.execute(query, (entry_id,))
    conn.commit()
    conn.close()

def get_detailed_budgets(hid, year):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT month, category_name, amount FROM budgets WHERE household_id = ? AND year = ?"
    params = (hid, year)
    log_query(query, params)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    data = {}
    for m, c, a in rows:
        if c not in data: data[c] = {}
        data[c][m] = a
    return data

def save_detailed_budget(hid, year, month, category_name, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "INSERT INTO budgets (household_id, year, month, category_name, amount) VALUES (?, ?, ?, ?, ?) ON CONFLICT(household_id, year, month, category_name) DO UPDATE SET amount = excluded.amount"
    params = (hid, year, month, category_name, amount)
    log_query(query, params)
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def save_detailed_budgets(hid, year, rows):
    """rows: [(month, category_name, amount)] - 한 트랜잭션으로 저장"""
    conn = get_db_connection()
    try:
        with conn:
            conn.executemany(
                "INSERT INTO budgets (household_id, year, month, category_name, amount) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(household_id, year, month, category_name) DO UPDATE SET amount = excluded.amount",
                [(hid, year, m, c, a) for m, c, a in rows]
            )
    finally:
        conn.close()

def clear_household_data(hid):
    """Wipes all data for a specific household."""
    conn = get_db_connection()
    try:
        with conn:
            _delete_household_rows(conn.cursor(), hid)
    finally:
        conn.close()

# --- Excel Migration Functions ---
def get_export_data(hid, year):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, type, parent_category, sub_category
        FROM categories
        WHERE household_id = ?
        ORDER BY type, parent_category, id
    """, (hid,))
    categories = cursor.fetchall()

    cursor.execute("""
        SELECT month, category_name, amount
        FROM budgets
        WHERE household_id = ? AND year = ?
        ORDER BY month, category_name
    """, (hid, year))
    budgets = cursor.fetchall()

    cursor.execute("""
        SELECT asset_name, initial_balance, current_balance
        FROM assets
        WHERE household_id = ?
        ORDER BY id
    """, (hid,))
    assets = cursor.fetchall()

    cursor.execute("""
        SELECT l.date, l.type, l.amount, l.memo, l.payee, l.payment_method,
               c.parent_category, c.sub_category,
               p.parent_category AS payment_parent, p.sub_category AS payment_name
        FROM ledgers l
        LEFT JOIN categories c ON l.category_id = c.id
        LEFT JOIN categories p ON l.asset_id = p.id
        WHERE l.household_id = ? AND l.date LIKE ?
        ORDER BY l.date ASC, l.id ASC
    """, (hid, f"{year}-%"))
    ledgers = cursor.fetchall()
    conn.close()
    return categories, budgets, assets, ledgers

def import_household_year(hid, year, categories, budgets, assets, ledgers):
    """Apply parsed Excel data in one transaction.

    categories: [(type, parent, sub)] - 기존 분류에 병합 (id 유지)
    budgets: [(month, category_name, amount)] - 해당 연도 예산 교체
    assets: [(asset_name, initial_balance)] - 같은 이름이면 금액 갱신
    ledgers: [dict(date, type, category, payment, amount, memo, payee, payment_method)]
        - 해당 연도 내역 교체. category/payment는 (type, parent, sub) 키
    """
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT OR IGNORE INTO categories (household_id, type, parent_category, sub_category, color) VALUES (?, ?, ?, ?, NULL)",
                [(hid, t, p, s) for t, p, s in categories]
            )
            cursor.executemany(
                "INSERT INTO assets (household_id, asset_name, initial_balance, current_balance) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(household_id, asset_name) DO UPDATE SET initial_balance = excluded.initial_balance, current_balance = excluded.current_balance",
                [(hid, name, amount, amount) for name, amount in assets]
            )
            cursor.execute("DELETE FROM budgets WHERE household_id = ? AND year = ?", (hid, year))
            cursor.executemany(
                "INSERT INTO budgets (household_id, year, month, category_name, amount) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(household_id, year, month, category_name) DO UPDATE SET amount = excluded.amount",
                [(hid, year, m, c, a) for m, c, a in budgets]
            )

            cursor.execute("SELECT id, type, parent_category, sub_category FROM categories WHERE household_id = ?", (hid,))
            cat_map = {(t, p, s): cid for cid, t, p, s in cursor.fetchall()}
            cursor.execute("DELETE FROM ledgers WHERE household_id = ? AND date LIKE ?", (hid, f"{year}-%"))
            cursor.executemany(
                "INSERT INTO ledgers (household_id, date, type, category_id, asset_id, amount, memo, payee, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(hid, e["date"], e["type"], cat_map.get(e["category"]), cat_map.get(e["payment"]) if e.get("payment") else None,
                  e["amount"], e["memo"], e["payee"], e["payment_method"]) for e in ledgers]
            )
    finally:
        conn.close()

# --- Report Aggregation Functions ---
def get_monthly_category_stats(hid, year, month):
    conn = get_db_connection()
    cursor = conn.cursor()
    month_str = f"{month:02d}"
    query = """
        SELECT c.parent_category, SUM(l.amount)
        FROM ledgers l
        JOIN categories c ON l.category_id = c.id
        WHERE l.household_id = ? AND l.type = '지출' AND l.date LIKE ?
        GROUP BY c.parent_category
    """
    params = (hid, f"{year}-{month_str}-%")
    log_query(query, params)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_monthly_daily_trends(hid, year, month):
    conn = get_db_connection()
    cursor = conn.cursor()
    month_str = f"{month:02d}"
    query = """
        SELECT SUBSTR(date, 9, 2) as day, SUM(amount)
        FROM ledgers
        WHERE household_id = ? AND type = '지출' AND date LIKE ?
        GROUP BY day
        ORDER BY day
    """
    params = (hid, f"{year}-{month_str}-%")
    log_query(query, params)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_yearly_monthly_trends(hid, year):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT SUBSTR(date, 6, 2) as month, type, SUM(amount)
        FROM ledgers
        WHERE household_id = ? AND date LIKE ?
        GROUP BY month, type
        ORDER BY month
    """
    params = (hid, f"{year}-%")
    log_query(query, params)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Process into dict {month: {'수입': X, '지출': Y}}
    data = {f"{m:02d}": {"수입": 0, "지출": 0} for m in range(1, 13)}
    for m, t, a in rows:
        if m in data: data[m][t] = a
    return data

if __name__ == "__main__":
    init_db()
