# scripts/migration.py
import sqlite3

def migrate():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()

    try:
        # Add columns to orders table
        cursor.execute("ALTER TABLE orders ADD COLUMN business_id VARCHAR(100)")
        cursor.execute("ALTER TABLE orders ADD COLUMN site_url VARCHAR(255)")
        cursor.execute("ALTER TABLE orders ADD COLUMN site_id VARCHAR(100)")
        print("Columns added to 'orders' table.")
    except sqlite3.OperationalError as e:
        print(f"Could not add columns to 'orders' table: {e}")

    # Create business_users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS business_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        business_id VARCHAR(100) UNIQUE NOT NULL,
        api_key VARCHAR(100) UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("'business_users' table created or already exists.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
