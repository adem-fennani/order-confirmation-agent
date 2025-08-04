# scripts/migration.py
import sqlite3

def migrate():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()

    # Create orders table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id VARCHAR(50) PRIMARY KEY,
        customer_name VARCHAR(100) NOT NULL,
        customer_phone VARCHAR(20) NOT NULL,
        items TEXT NOT NULL,
        total_amount REAL NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        confirmed_at DATETIME,
        notes TEXT,
        delivery_address TEXT,
        business_id VARCHAR(100),
        site_url VARCHAR(255),
        site_id VARCHAR(100)
    )
    """)
    print("'orders' table created or already exists.")

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