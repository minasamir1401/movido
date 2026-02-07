
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import logging

logger = logging.getLogger("admin_auth")

# Security configuration
SECRET_KEY = "MOVIDO_SUPER_SECRET_KEY_2026_SECURE_DASHBOARD"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Admin credentials (hashed)
ADMIN_CREDENTIALS = {
    "username": "mina samir",
    "password_hash": hashlib.sha256("!9#@minasamir#@".encode()).hexdigest(),
    "connection_key": "en"  # Extra security layer
}

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired. Please login again."
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Dependency to verify admin authentication.
    Use this on protected endpoints.
    """
    token = credentials.credentials
    try:
        payload = verify_token(token)
        username = payload.get("sub")
        if username != ADMIN_CREDENTIALS["username"]:
            raise HTTPException(status_code=403, detail="Unauthorized access")
        return username
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

def authenticate_admin(username: str, password: str, connection_key: str) -> bool:
    """
    Verify admin credentials with 3-layer security:
    1. Username check
    2. Password hash verification
    3. Connection key validation
    """
    if username != ADMIN_CREDENTIALS["username"]:
        logger.warning(f"Failed login attempt: Invalid username '{username}'")
        return False
    
    if not verify_password(password, ADMIN_CREDENTIALS["password_hash"]):
        logger.warning(f"Failed login attempt: Invalid password for '{username}'")
        return False
    
    if connection_key != ADMIN_CREDENTIALS["connection_key"]:
        logger.warning(f"Failed login attempt: Invalid connection key for '{username}'")
        return False
    
    logger.info(f"✅ Successful admin login: {username}")
    return True
