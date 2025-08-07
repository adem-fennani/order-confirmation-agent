# scripts/create_test_user.py
import os
import sys
import asyncio

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent.database.sqlite import SQLiteDatabase
from src.agent.database.models import BusinessUser
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


def create_test_user():
    # Use a synchronous engine for this script
    engine = create_engine("sqlite:///orders.db")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Check if user exists
    user = session.query(BusinessUser).filter_by(username="admin").first()
    if user:
        print(f"Admin user already exists with API key: {user.api_key}")
        return

    # Create user
    new_user = BusinessUser(
        username="admin",
        business_id="admin_business",
        api_key=BusinessUser.generate_api_key()
    )
    new_user.set_password("admin123")
    
    session.add(new_user)
    session.commit()

    print(f"Admin user created with API key: {new_user.api_key}")

if __name__ == "__main__":
    create_test_user()