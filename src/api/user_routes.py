from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from ..storage.user_storage import get_users, add_user, generate_api_key
from ..database.connection import get_db
from ..database.models import User, APIKey
from .auth import get_current_user, hash_key

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current user information"""
    return user.to_dict()

@router.get("/list")
async def list_users(user: User = Depends(get_current_user)):
    """List all users (admin only)"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return get_users()

@router.post("/")
async def create_user(data: dict, user: User = Depends(get_current_user)):
    """Create a new user (admin only)"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    success = add_user(data)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to create user")
    
    return {"status": "success", "message": "User created"}

@router.post("/{user_id}/keys")
async def create_api_key(user_id: int, label: str = "Default", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a new API key for a user (admin only)"""
    if not user.is_admin and user.id != user_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    raw_key = generate_api_key()
    hashed_key = hash_key(raw_key)
    
    new_key = APIKey(
        user_id=user_id,
        key_hash=hashed_key,
        label=label
    )
    
    db.add(new_key)
    db.commit()
    
    return {
        "status": "success",
        "api_key": raw_key,
        "message": "Write this key down, it won't be shown again!"
    }
