import sqlite3
import os

DB_NAME = "household.db"

def init_db():
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
                print(f"Repairing {table}: UNIQUE constraint missing household_id. Recreating...")
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                cursor.execute(create_sql)
                conn.commit()

    # Ledgers migration (Individual columns)
    cursor.execute(f"PRAGMA table_info(ledgers)")
    l_cols = [row[1] for row in cursor.fetchall()]
    if "household_id" not in l_cols:
        cursor.execute(f"ALTER TABLE ledgers ADD COLUMN household_id INTEGER REFERENCES households(id)")
        cursor.execute(f"UPDATE ledgers SET household_id = ?", (default_hid,))
    if "payee" not in l_cols: cursor.execute("ALTER TABLE ledgers ADD COLUMN payee TEXT")
    if "payment_method" not in l_cols: cursor.execute("ALTER TABLE ledgers ADD COLUMN payment_method TEXT")
    
    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} initialized correctly.")

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def log_query(query, params=None):
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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM households WHERE id = ?", (hid,))
    conn.commit()
    conn.close()

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
    query = "INSERT INTO categories (household_id, type, parent_category, sub_category) VALUES (?, ?, ?, ?)"
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
        query = "SELECT id, type, parent_category, sub_category FROM categories WHERE household_id = ? AND type = ?"
        params = (hid, category_type)
    else:
        query = "SELECT id, type, parent_category, sub_category FROM categories WHERE household_id = ?"
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
        if entry_type == "수입":
            cursor.execute("UPDATE assets SET current_balance = current_balance + ? WHERE id = ?", (amount, asset_id))
        elif entry_type == "지출":
            cursor.execute("UPDATE assets SET current_balance = current_balance - ? WHERE id = ?", (amount, asset_id))
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
        cursor.execute("SELECT type, amount, asset_id FROM ledgers WHERE id = ?", (entry_id,))
        old = cursor.fetchone()
        if old:
            ot, oa, oaid = old
            if ot == "수입": cursor.execute("UPDATE assets SET current_balance = current_balance - ? WHERE id = ?", (oa, oaid))
            elif ot == "지출": cursor.execute("UPDATE assets SET current_balance = current_balance + ? WHERE id = ?", (oa, oaid))

        query = "UPDATE ledgers SET date=?, type=?, category_id=?, asset_id=?, amount=?, memo=?, payee=?, payment_method=? WHERE id=?"
        params = (date, entry_type, category_id, asset_id, amount, memo, payee, payment_method, entry_id)
        log_query(query, params)
        cursor.execute(query, params)

        if entry_type == "수입": cursor.execute("UPDATE assets SET current_balance = current_balance + ? WHERE id = ?", (amount, asset_id))
        elif entry_type == "지출": cursor.execute("UPDATE assets SET current_balance = current_balance - ? WHERE id = ?", (amount, asset_id))
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
               c.parent_category, c.sub_category, p.sub_category as asset_name
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
    cursor.execute("SELECT type, amount, asset_id FROM ledgers WHERE id = ?", (entry_id,))
    entry = cursor.fetchone()
    if entry:
        et, am, aid = entry
        if et == "수입": cursor.execute("UPDATE assets SET current_balance = current_balance - ? WHERE id = ?", (am, aid))
        elif et == "지출": cursor.execute("UPDATE assets SET current_balance = current_balance + ? WHERE id = ?", (am, aid))
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

def clear_household_data(hid):
    """Wipes all data for a specific household."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE household_id = ?", (hid,))
    cursor.execute("DELETE FROM budgets WHERE household_id = ?", (hid,))
    cursor.execute("DELETE FROM assets WHERE household_id = ?", (hid,))
    cursor.execute("DELETE FROM ledgers WHERE household_id = ?", (hid,))
    conn.commit()
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
