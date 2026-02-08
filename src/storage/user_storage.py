"""
Database-backed user storage with Redis caching
Replaces users.json with PostgreSQL
"""
import logging
import secrets
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from ..database import db_manager, User
from ..cache import redis_cache

logger = logging.getLogger(__name__)


def get_users() -> List[Dict]:
    """
    Get all active users
    
    Returns:
        List of user dictionaries
    """
    with db_manager.get_session() as session:
        users = session.query(User).filter_by(is_active=True).order_by(User.display_name).all()
        return [u.to_dict() for u in users]


def get_user_by_key(api_key: str) -> Optional[Dict]:
    """
    Get user by API key with Redis caching
    
    Args:
        api_key: User's API key
    
    Returns:
        User dictionary or None
    """
    # Check if key is blacklisted
    if redis_cache.is_key_blacklisted(api_key):
        logger.warning(f"Attempted use of blacklisted API key: {api_key[:10]}...")
        return None
    
    # Try cache first
    cached_user = redis_cache.get_user(api_key)
    if cached_user:
        return cached_user
    
    # Query database
    with db_manager.get_session() as session:
        user = session.query(User).filter_by(api_key=api_key, is_active=True).first()
        
        if user:
            user_dict = user.to_dict()
            # Cache for 5 minutes
            redis_cache.set_user(api_key, user_dict, ttl=300)
            return user_dict
        
        return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """
    Get user by ID
    
    Args:
        user_id: User ID
    
    Returns:
        User dictionary or None
    """
    with db_manager.get_session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        
        if user:
            return user.to_dict()
        
        return None


def add_user(user_data: Dict) -> bool:
    """
    Add a new user
    
    Args:
        user_data: Dict with 'name', 'display_name', optional 'api_key', 'avatar_url', etc.
    
    Returns:
        True if successful
    """
    try:
        with db_manager.get_session() as session:
            # Generate API key if not provided
            api_key = user_data.get('api_key') or generate_api_key()
            
            # Create user
            user = User(
                name=user_data.get('name', user_data.get('display_name')),
                display_name=user_data.get('display_name'),
                api_key=api_key,
                avatar_url=user_data.get('avatar_url') or user_data.get('avatar'),
                gemini_api_key=user_data.get('gemini_api_key'),
                google_maps_api_key=user_data.get('google_maps_api_key'),
                is_active=user_data.get('is_active', True),
                is_admin=user_data.get('is_admin', False)
            )
            
            session.add(user)
            session.commit()
            
            logger.info(f"User created: {user.display_name} (ID: {user.id})")
            return True
            
    except Exception as e:
        logger.error(f"Failed to add user: {e}")
        return False


def update_user(user_id: int, user_data: Dict) -> bool:
    """
    Update an existing user
    
    Args:
        user_id: User ID
        user_data: Dict with fields to update
    
    Returns:
        True if successful
    """
    try:
        with db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.error(f"User not found: {user_id}")
                return False
            
            # Update fields
            if 'name' in user_data:
                user.name = user_data['name']
            if 'display_name' in user_data:
                user.display_name = user_data['display_name']
            if 'avatar_url' in user_data or 'avatar' in user_data:
                user.avatar_url = user_data.get('avatar_url') or user_data.get('avatar')
            if 'gemini_api_key' in user_data:
                user.gemini_api_key = user_data['gemini_api_key']
            if 'google_maps_api_key' in user_data:
                user.google_maps_api_key = user_data['google_maps_api_key']
            if 'is_active' in user_data:
                user.is_active = user_data['is_active']
            if 'is_admin' in user_data:
                user.is_admin = user_data['is_admin']
            
            session.commit()
            
            # Invalidate cache
            redis_cache.invalidate_user(user.api_key)
            
            logger.info(f"User updated: {user.display_name} (ID: {user.id})")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        return False


def delete_user(user_id: int) -> bool:
    """
    Soft delete a user (set is_active=False)
    
    Args:
        user_id: User ID
    
    Returns:
        True if successful
    """
    try:
        with db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.error(f"User not found: {user_id}")
                return False
            
            # Soft delete
            user.is_active = False
            session.commit()
            
            # Blacklist API key
            redis_cache.blacklist_key(user.api_key)
            
            # Invalidate cache
            redis_cache.invalidate_user(user.api_key)
            
            logger.info(f"User deactivated: {user.display_name} (ID: {user.id})")
            return True
            
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        return False


def reset_user_key(user_id: int) -> Optional[str]:
    """
    Reset user's API key (CA.ADM.3)
    
    Args:
        user_id: User ID
    
    Returns:
        New API key or None
    """
    try:
        with db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.error(f"User not found: {user_id}")
                return None
            
            # Blacklist old key
            old_key = user.api_key
            redis_cache.blacklist_key(old_key)
            redis_cache.invalidate_user(old_key)
            
            # Generate new key
            new_key = generate_api_key()
            user.api_key = new_key
            
            session.commit()
            
            logger.info(f"API key reset for user: {user.display_name} (ID: {user.id})")
            return new_key
            
    except Exception as e:
        logger.error(f"Failed to reset user key: {e}")
        return None


def generate_api_key() -> str:
    """
    Generate a secure API key
    
    Returns:
        Random API key
    """
    return secrets.token_urlsafe(32)


def save_users(users: List[Dict]) -> bool:
    """
    Legacy compatibility function (not recommended)
    Use add_user/update_user instead
    """
    logger.warning("save_users() is deprecated, use add_user/update_user instead")
    return False
