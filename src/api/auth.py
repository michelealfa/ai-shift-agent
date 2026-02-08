import hashlib
import logging
from fastapi import Header, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from typing import Optional

from ..database.connection import get_db
from ..database.models import User, APIKey
from ..config.config import settings

logger = logging.getLogger(__name__)

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def hash_key(key: str) -> str:
    """Hash the API key for storage/lookup"""
    return hashlib.sha256(key.encode()).hexdigest()

async def get_current_user(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from the API Key.
    Validates the key against the hashed values in the database.
    """
    if not api_key:
        raise HTTPException(
            status_code=403, detail="API Key missing"
        )

    # Check for master/internal key (for admin/system tasks)
    if api_key == settings.INTERNAL_API_KEY:
        # Return the first admin user or a system user
        user = db.query(User).filter_by(is_admin=True, is_active=True).first()
        if user:
            return user
        raise HTTPException(
            status_code=403, detail="No admin user found for internal key"
        )

    # Hash the provided key to compare with DB
    hashed_key = hash_key(api_key)
    
    # Lookup the key
    api_key_record = db.query(APIKey).filter_by(
        key_hash=hashed_key, 
        is_active=True
    ).first()

    if not api_key_record:
        logger.warning(f"Invalid API Key attempt: {api_key[:10]}...")
        raise HTTPException(
            status_code=403, detail="Invalid API Key"
        )

    # Get the user
    user = db.query(User).filter_by(id=api_key_record.user_id, is_active=True).first()
    
    if not user:
        raise HTTPException(
            status_code=403, detail="User associated with this key is inactive or not found"
        )

    return user

async def get_optional_user(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional version of get_current_user"""
    try:
        return await get_current_user(api_key, db)
    except HTTPException:
        return None
