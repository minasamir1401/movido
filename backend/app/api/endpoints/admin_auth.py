
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import timedelta
from ...core.admin_auth import (
    authenticate_admin,
    create_access_token,
    get_current_admin,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
import logging

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])
logger = logging.getLogger("api.admin.auth")

class AdminLogin(BaseModel):
    username: str
    password: str
    connection_key: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

@router.post("/login", response_model=TokenResponse)
async def admin_login(credentials: AdminLogin):
    """
    🔐 Admin Dashboard Login
    
    Requires 3-layer authentication:
    - Username: mina samir
    - Password: !9#@minasamir#@
    - Connection Key: en
    
    Returns a JWT token valid for 60 minutes.
    """
    # Validate credentials
    if not authenticate_admin(
        credentials.username,
        credentials.password,
        credentials.connection_key
    ):
        # Generic error message to prevent username enumeration
        raise HTTPException(
            status_code=401,
            detail="⛔ Authentication failed. Invalid credentials or connection key."
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": credentials.username},
        expires_delta=access_token_expires
    )
    
    logger.info(f"✅ Token issued for admin: {credentials.username}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
    }

@router.get("/verify")
async def verify_admin_token(current_admin: str = Depends(get_current_admin)):
    """
    Verify if the current token is valid.
    Protected endpoint - requires valid JWT token.
    """
    return {
        "valid": True,
        "admin": current_admin,
        "message": "✅ Token is valid"
    }

@router.post("/logout")
async def admin_logout(current_admin: str = Depends(get_current_admin)):
    """
    Logout endpoint (client should discard the token).
    Protected endpoint - requires valid JWT token.
    """
    logger.info(f"Admin logged out: {current_admin}")
    return {
        "success": True,
        "message": "Logged out successfully. Please discard your token."
    }
