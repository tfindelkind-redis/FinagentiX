"""
Authentication module for FinagentiX API
Simple JWT-based authentication for demo/showcase environment
"""

import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel


# ==================== Configuration ====================

# Get auth credentials from environment (required - no defaults for security)
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")  # Required - no default!
if not AUTH_PASSWORD:
    raise ValueError("AUTH_PASSWORD environment variable is required")
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is required")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


# ==================== Models ====================

class LoginRequest(BaseModel):
    """Login request body"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response with JWT token"""
    token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    username: str


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # username
    exp: datetime
    iat: datetime


class User(BaseModel):
    """Current user info"""
    username: str
    authenticated: bool = True


# ==================== Password Utilities ====================

def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    Verify a password - for demo we use simple comparison
    since passwords come from env vars (not user-provided)
    """
    return plain_password == stored_password


# ==================== JWT Utilities ====================

def create_access_token(username: str) -> tuple[str, int]:
    """
    Create a JWT access token
    Returns: (token, expires_in_seconds)
    """
    expires_delta = timedelta(hours=JWT_EXPIRY_HOURS)
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    expires_in = int(expires_delta.total_seconds())
    
    return token, expires_in


def decode_token(token: str) -> Optional[TokenPayload]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
        )
    except JWTError:
        return None


# ==================== Authentication Functions ====================

def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate user with username and password
    For demo: single user from environment variables
    """
    if username != AUTH_USERNAME:
        return None
    
    # Verify password (simple comparison for demo)
    if not verify_password(password, AUTH_PASSWORD):
        return None
    
    return User(username=username)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    Raises 401 if not authenticated
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if credentials is None:
        raise credentials_exception
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    # Check if token is expired
    if datetime.utcnow() > payload.exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return User(username=payload.sub)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Dependency to get current user if authenticated, None otherwise
    Does not raise an exception for unauthenticated requests
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ==================== Login Handler ====================

def login(username: str, password: str) -> LoginResponse:
    """
    Handle login request
    Returns JWT token on success, raises 401 on failure
    """
    user = authenticate_user(username, password)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token, expires_in = create_access_token(user.username)
    
    return LoginResponse(
        token=token,
        expires_in=expires_in,
        username=user.username,
    )
