"""
FastAPI authentication dependencies for Firebase token verification.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.services.firebase_auth import get_user_id_from_token

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    FastAPI dependency to get current authenticated user ID from Firebase token.
    
    Extracts Bearer token from Authorization header, verifies it with Firebase,
    and returns the user ID (uid).
    
    Args:
        credentials: HTTP Bearer credentials from Authorization header
        
    Returns:
        User ID (uid) string from Firebase token
        
    Raises:
        HTTPException(401): If token is missing, invalid, or expired
    """
    token = credentials.credentials
    
    try:
        user_id = get_user_id_from_token(token)
        return user_id
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[str]:
    """
    Optional authentication dependency - returns user_id if token is present and valid,
    otherwise returns None.
    
    Useful for routes that can work with or without authentication.
    
    Args:
        credentials: Optional HTTP Bearer credentials from Authorization header
        
    Returns:
        User ID (uid) string if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        user_id = get_user_id_from_token(token)
        return user_id
    except Exception:
        # If token is invalid, return None (optional auth)
        return None

