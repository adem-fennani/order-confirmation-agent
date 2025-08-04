# src/api/business.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from src.api.dependencies import verify_api_key, get_db
from src.agent.database.models import BusinessUser

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

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_db)):
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
    user = session.query(BusinessUser).filter_by(username=username).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/api/business/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_db)):
    user = session.query(BusinessUser).filter_by(username=form_data.username).first()
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

@router.get("/api/business/me")
async def read_users_me(current_user: BusinessUser = Depends(get_current_user)):
    return current_user


@router.get("/api/business/test")
async def test_api_key(user: BusinessUser = Depends(verify_api_key)):
    return {"message": f"API Key is valid for business: {user.business_id}"}
