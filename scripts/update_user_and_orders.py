
import sqlite3

def update_db():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()

    # Delete the testuser
    cursor.execute("DELETE FROM business_users WHERE username = 'testuser'")
    print("Deleted user: testuser")

    # Reassign orders from test_business to admin_business
    cursor.execute("UPDATE orders SET business_id = 'admin_business' WHERE business_id = 'test_business'")
    print("Reassigned orders to admin_business")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_db()
