# src/api/business.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List
from src.api.dependencies import verify_api_key, get_db_interface
from src.agent.database.models import BusinessUser, OrderModel
from src.api.schemas import Order, BusinessUserSchema
from src.agent.database.sqlite import SQLiteDatabase

router = APIRouter()

SECRET_KEY = "your-secret-key"  # In a real app, use a more secure key and load from config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# In-memory storage for tokens (for MVP)
session_storage = {}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/business/login")

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: SQLiteDatabase = Depends(get_db_interface)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Use async db method
    user = await db.get_business_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user

@router.post("/api/business/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: SQLiteDatabase = Depends(get_db_interface)):
    # Use async db method
    user = await db.get_business_user_by_username(form_data.username)
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "business_id": user.business_id},
        expires_delta=access_token_expires
    )
    session_storage[access_token] = user.username # Store token
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/api/business/me", response_model=BusinessUserSchema)
async def read_users_me(current_user: BusinessUser = Depends(get_current_user)):
    return current_user

@router.get("/api/business/orders", response_model=List[Order])
async def get_business_orders(skip: int = 0, limit: int = 10, current_user: BusinessUser = Depends(get_current_user), db: SQLiteDatabase = Depends(get_db_interface)):
    # Use async db method
    orders = await db.get_orders_by_business_id(current_user.business_id, skip=skip, limit=limit)
    return orders

@router.get("/api/business/orders/{order_id}", response_model=Order)
async def get_business_order(order_id: str, current_user: BusinessUser = Depends(get_current_user), db: SQLiteDatabase = Depends(get_db_interface)):
    # Use async db method
    order = await db.get_order_by_business_id(order_id, current_user.business_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.get("/api/business/api-key")
async def get_business_api_key(current_user: BusinessUser = Depends(get_current_user)):
    if not current_user.api_key:
        raise HTTPException(status_code=404, detail="API Key not found for this business.")
    return {"api_key": current_user.api_key}

@router.get("/api/business/test")
async def test_api_key(user: BusinessUser = Depends(verify_api_key)):
    return {"message": f"API Key is valid for business: {user.business_id}"}