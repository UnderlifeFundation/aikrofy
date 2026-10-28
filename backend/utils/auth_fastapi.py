import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from config import get_config
from models.user import User
from database import get_db

config = get_config()
JWT_SECRET_KEY = config.JWT_SECRET_KEY
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire, "sub": str(data.get("sub"))})
    # Add iat for compatibility with flask-jwt-extended if needed
    to_encode.update({"iat": datetime.utcnow()})
    # flask-jwt-extended uses 'sub' for identity.
    # It also adds 'jti' (JWT ID) and 'type' (access/refresh).
    if "type" not in to_encode:
        to_encode["type"] = "access"
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire, "sub": str(data.get("sub")), "iat": datetime.utcnow(), "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_id(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Remove "Bearer " if present (sometimes oauth2_scheme doesn't)
        if token.startswith("Bearer "):
            token = token[7:]
            
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        # Security: reject refresh tokens used as access tokens
        token_type = payload.get("type", "access")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: refresh tokens cannot be used for authentication",
            )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing sub",
            )
        return int(user_id)
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user_id = get_current_user_id(token)
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

def get_current_user_and_company(user: User = Depends(get_current_user)):
    if not user.company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No company associated with this user",
        )
    return user, user.company

