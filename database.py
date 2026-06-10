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
        type TEXT NOT NULL, -- '소비', '소득', '결제수단', '자본', '부채'
        parent_category TEXT NOT NULL, -- 대분류
        sub_category TEXT NOT NULL, -- 중분류
        UNIQUE(type, parent_category, sub_category)
    )
    """)

    # 2. Monthly Budgets Table (Category-independent)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monthly_budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        amount INTEGER DEFAULT 0,
        UNIQUE(year, month)
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

    # 4. Ledgers Table (Updated for Payee and specific columns)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledgers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL, -- YYYY-MM-DD
        type TEXT NOT NULL, -- '수입', '지출', '이체'
        category_id INTEGER,
        asset_id INTEGER,
        amount INTEGER NOT NULL,
        memo TEXT,
        payee TEXT, -- 사용처 / 소득처
        payment_method TEXT, -- '신용카드', '은행' 등 (참고용)
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (asset_id) REFERENCES assets (id)
    )
    """)

    conn.commit()

    # --- Migration: Add missing columns if they don't exist ---
    cursor.execute("PRAGMA table_info(ledgers)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "payee" not in columns:
        cursor.execute("ALTER TABLE ledgers ADD COLUMN payee TEXT")
    if "payment_method" not in columns:
        cursor.execute("ALTER TABLE ledgers ADD COLUMN payment_method TEXT")
        
    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} initialized successfully.")

def get_db_connection():
    return sqlite3.connect(DB_NAME)

# --- Category Functions ---
def add_category(category_type, parent, sub):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (type, parent_category, sub_category) VALUES (?, ?, ?)",
                       (category_type, parent, sub))
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
        cursor.execute("SELECT id, type, parent_category, sub_category FROM categories WHERE type = ?", (category_type,))
    else:
        cursor.execute("SELECT id, type, parent_category, sub_category FROM categories")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()

def delete_category_by_parent(db_type, parent_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE type = ? AND parent_category = ?", (db_type, parent_name))
    conn.commit()
    conn.close()

# --- Asset Functions ---
def add_asset(name, initial_balance):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO assets (asset_name, initial_balance, current_balance) VALUES (?, ?, ?)",
                       (name, initial_balance, initial_balance))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_assets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, asset_name, initial_balance, current_balance FROM assets")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_asset(asset_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    conn.commit()
    conn.close()

# --- Ledger Functions ---
def add_ledger_entry(date, entry_type, category_id, asset_id, amount, memo, payee, payment_method):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO ledgers (date, type, category_id, asset_id, amount, memo, payee, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, entry_type, category_id, asset_id, amount, memo, payee, payment_method))
        
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
        # Get old values to revert balance
        cursor.execute("SELECT type, amount, asset_id FROM ledgers WHERE id = ?", (entry_id,))
        old = cursor.fetchone()
        if old:
            old_type, old_amount, old_asset_id = old
            if old_type == "수입":
                cursor.execute("UPDATE assets SET current_balance = current_balance - ? WHERE id = ?", (old_amount, old_asset_id))
            elif old_type == "지출":
                cursor.execute("UPDATE assets SET current_balance = current_balance + ? WHERE id = ?", (old_amount, old_asset_id))

        # Update ledger
        cursor.execute("""
            UPDATE ledgers SET date=?, type=?, category_id=?, asset_id=?, amount=?, memo=?, payee=?, payment_method=? WHERE id=?
        """, (date, entry_type, category_id, asset_id, amount, memo, payee, payment_method, entry_id))

        # Apply new balance
        if entry_type == "수입":
            cursor.execute("UPDATE assets SET current_balance = current_balance + ? WHERE id = ?", (amount, asset_id))
        elif entry_type == "지출":
            cursor.execute("UPDATE assets SET current_balance = current_balance - ? WHERE id = ?", (amount, asset_id))
            
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
    date_pattern = f"{year}-{month_str}-%"
    
    cursor.execute("""
        SELECT l.id, l.date, l.type, l.category_id, l.asset_id, l.amount, l.memo, l.payee, l.payment_method,
               c.parent_category, c.sub_category, a.asset_name
        FROM ledgers l
        LEFT JOIN categories c ON l.category_id = c.id
        LEFT JOIN assets a ON l.asset_id = a.id
        WHERE l.date LIKE ?
        ORDER BY l.date ASC, l.id ASC
    """, (date_pattern,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_ledger_entry(entry_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT type, amount, asset_id FROM ledgers WHERE id = ?", (entry_id,))
    entry = cursor.fetchone()
    if entry:
        entry_type, amount, asset_id = entry
        if entry_type == "수입":
            cursor.execute("UPDATE assets SET current_balance = current_balance - ? WHERE id = ?", (amount, asset_id))
        elif entry_type == "지출":
            cursor.execute("UPDATE assets SET current_balance = current_balance + ? WHERE id = ?", (amount, asset_id))
        
        cursor.execute("DELETE FROM ledgers WHERE id = ?", (entry_id,))
        conn.commit()
    conn.close()

# --- Budget Functions (New Table) ---
def get_monthly_budgets(year):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT month, amount FROM monthly_budgets WHERE year = ?", (year,))
    rows = cursor.fetchall()
    conn.close()
    return {month: amount for month, amount in rows}

def save_monthly_budget(year, month, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO monthly_budgets (year, month, amount)
        VALUES (?, ?, ?)
        ON CONFLICT(year, month) DO UPDATE SET amount = excluded.amount
    """, (year, month, amount))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
