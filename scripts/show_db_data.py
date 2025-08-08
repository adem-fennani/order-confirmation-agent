
import sqlite3

def show_db_data():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()

    print("--- Business Users ---")
    cursor.execute("SELECT id, username, business_id, api_key FROM business_users")
    for row in cursor.fetchall():
        print(row)

    print("\n--- Orders ---")
    cursor.execute("SELECT id, customer_name, total_amount, business_id, site_url FROM orders")
    for row in cursor.fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    show_db_data()
