import sqlite3
import os

DB_NAME = "household.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Categories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL, 
        parent_category TEXT NOT NULL, 
        sub_category TEXT NOT NULL, 
        UNIQUE(type, parent_category, sub_category)
    )
    """)

    # 2. Budgets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        category_name TEXT NOT NULL,
        amount INTEGER DEFAULT 0,
        UNIQUE(year, month, category_name)
    )
    """)

    # 3. Assets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_name TEXT NOT NULL UNIQUE,
        initial_balance INTEGER DEFAULT 0,
        current_balance INTEGER DEFAULT 0
    )
    """)

    # 4. Ledgers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledgers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL, 
        type TEXT NOT NULL, 
        category_id INTEGER,
        asset_id INTEGER,
        amount INTEGER NOT NULL,
        memo TEXT,
        payee TEXT,
        payment_method TEXT,
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (asset_id) REFERENCES assets (id)
    )
    """)

    conn.commit()

    # --- Migration: Ledgers ---
    cursor.execute("PRAGMA table_info(ledgers)")
    columns = [row[1] for row in cursor.fetchall()]
    if "payee" not in columns:
        cursor.execute("ALTER TABLE ledgers ADD COLUMN payee TEXT")
    if "payment_method" not in columns:
        cursor.execute("ALTER TABLE ledgers ADD COLUMN payment_method TEXT")
        
    # --- Migration: Budgets ---
    cursor.execute("PRAGMA table_info(budgets)")
    b_columns = [row[1] for row in cursor.fetchall()]
    if "category_name" not in b_columns and len(b_columns) > 0:
        cursor.execute("DROP TABLE budgets")
        cursor.execute("""
        CREATE TABLE budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            category_name TEXT NOT NULL,
            amount INTEGER DEFAULT 0,
            UNIQUE(year, month, category_name)
        )
        """)

    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} initialized successfully.")

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def log_query(query, params=None):
    print(f"\n[DB LOG] {query.strip()}")
    if params: print(f"        {params}")

# --- Category Functions ---
def add_category(category_type, parent, sub):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "INSERT INTO categories (type, parent_category, sub_category) VALUES (?, ?, ?)"
    params = (category_type, parent, sub)
    log_query(query, params)
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_categories(category_type=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if category_type:
        query = "SELECT id, type, parent_category, sub_category FROM categories WHERE type = ?"
        params = (category_type,)
    else:
        query = "SELECT id, type, parent_category, sub_category FROM categories"
        params = None
    log_query(query, params)
    cursor.execute(query, params) if params else cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "DELETE FROM categories WHERE id = ?"
    params = (category_id,)
    log_query(query, params)
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def delete_category_by_parent(db_type, parent_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "DELETE FROM categories WHERE type = ? AND parent_category = ?"
    params = (db_type, parent_name)
    log_query(query, params)
    cursor.execute(query, params)
    conn.commit()
    conn.close()

# --- Asset Functions ---
def add_asset(name, initial_balance):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "INSERT INTO assets (asset_name, initial_balance, current_balance) VALUES (?, ?, ?)"
    params = (name, initial_balance, initial_balance)
    log_query(query, params)
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_assets():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT id, asset_name, initial_balance, current_balance FROM assets"
    log_query(query)
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_asset(asset_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "DELETE FROM assets WHERE id = ?"
    params = (asset_id,)
    log_query(query, params)
    cursor.execute(query, params)
    conn.commit()
    conn.close()

# --- Ledger Functions ---
def add_ledger_entry(date, entry_type, category_id, asset_id, amount, memo, payee, payment_method):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "INSERT INTO ledgers (date, type, category_id, asset_id, amount, memo, payee, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        params = (date, entry_type, category_id, asset_id, amount, memo, payee, payment_method)
        log_query(query, params)
        cursor.execute(query, params)
        
        # Update asset balance
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

def get_ledger_entries(year, month):
    conn = get_db_connection()
    cursor = conn.cursor()
    month_str = f"{month:02d}"
    query = """
        SELECT l.id, l.date, l.type, l.category_id, l.asset_id, l.amount, l.memo, l.payee, l.payment_method,
               c.parent_category, c.sub_category, p.sub_category as asset_name
        FROM ledgers l
        LEFT JOIN categories c ON l.category_id = c.id
        LEFT JOIN categories p ON l.asset_id = p.id
        WHERE l.date LIKE ?
        ORDER BY l.date ASC, l.id ASC
    """
    params = (f"{year}-{month_str}-%",)
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

def get_detailed_budgets(year):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT month, category_name, amount FROM budgets WHERE year = ?"
    log_query(query, (year,))
    cursor.execute(query, (year,))
    rows = cursor.fetchall()
    conn.close()
    data = {}
    for m, c, a in rows:
        if c not in data: data[c] = {}
        data[c][m] = a
    return data

def save_detailed_budget(year, month, category_name, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "INSERT INTO budgets (year, month, category_name, amount) VALUES (?, ?, ?, ?) ON CONFLICT(year, month, category_name) DO UPDATE SET amount = excluded.amount"
    params = (year, month, category_name, amount)
    log_query(query, params)
    cursor.execute(query, params)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
