"""
Database-backed settings storage
Replaces dynamic_settings.json with PostgreSQL
"""
import logging
from typing import Optional, Dict
from sqlalchemy.orm import Session

from ..database import db_manager, SystemSetting
from ..cache import redis_cache

logger = logging.getLogger(__name__)


class SettingsStorage:
    """Manages system settings in PostgreSQL with Redis caching"""
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a setting value
        
        Args:
            key: Setting key
            default: Default value if not found
        
        Returns:
            Setting value or default
        """
        # Try cache first
        cached = redis_cache.get_setting(key)
        if cached is not None:
            return cached
        
        # Query database
        with db_manager.get_session() as session:
            setting = session.query(SystemSetting).filter_by(key=key).first()
            
            if setting:
                # Cache the value
                redis_cache.set_setting(key, setting.value)
                return setting.value
            
            return default
    
    def set_setting(
        self, 
        key: str, 
        value: str, 
        description: Optional[str] = None,
        updated_by: Optional[int] = None
    ) -> bool:
        """
        Set a setting value
        
        Args:
            key: Setting key
            value: Setting value
            description: Optional description
            updated_by: User ID who updated the setting
        
        Returns:
            True if successful
        """
        try:
            with db_manager.get_session() as session:
                setting = session.query(SystemSetting).filter_by(key=key).first()
                
                if setting:
                    # Update existing
                    setting.value = value
                    if description:
                        setting.description = description
                    if updated_by:
                        setting.updated_by = updated_by
                else:
                    # Create new
                    setting = SystemSetting(
                        key=key,
                        value=value,
                        description=description,
                        updated_by=updated_by
                    )
                    session.add(setting)
                
                session.commit()
            
            # Invalidate cache
            redis_cache.invalidate_setting(key)
            
            logger.info(f"Setting updated: {key} = {value[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, str]:
        """
        Get all settings as a dictionary
        
        Returns:
            Dict of key-value pairs
        """
        with db_manager.get_session() as session:
            settings = session.query(SystemSetting).all()
            return {s.key: s.value for s in settings}
    
    def delete_setting(self, key: str) -> bool:
        """
        Delete a setting
        
        Args:
            key: Setting key
        
        Returns:
            True if deleted, False if not found
        """
        try:
            with db_manager.get_session() as session:
                setting = session.query(SystemSetting).filter_by(key=key).first()
                
                if setting:
                    session.delete(setting)
                    session.commit()
                    
                    # Invalidate cache
                    redis_cache.invalidate_setting(key)
                    
                    logger.info(f"Setting deleted: {key}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete setting {key}: {e}")
            return False
    
    # Convenience methods for common settings
    
    def get_vision_model(self) -> str:
        """Get vision model setting"""
        return self.get_setting('VISION_MODEL', 'gemini-2.5-flash')
    
    def get_nlp_model(self) -> str:
        """Get NLP model setting"""
        return self.get_setting('NLP_MODEL', 'gemini-2.5-flash')
    
    def get_gemini_api_key(self, user_id: Optional[int] = None) -> Optional[str]:
        """
        Get Gemini API key (user-specific or global)
        
        Args:
            user_id: Optional user ID for user-specific key
        
        Returns:
            API key or None
        """
        # Try user-specific key first
        if user_id:
            from ..database import User
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if user and user.gemini_api_key:
                    return user.gemini_api_key
        
        # Fall back to global setting
        return self.get_setting('GEMINI_API_KEY')
    
    def get_google_maps_api_key(self, user_id: Optional[int] = None) -> Optional[str]:
        """
        Get Google Maps API key (user-specific or global)
        
        Args:
            user_id: Optional user ID for user-specific key
        
        Returns:
            API key or None
        """
        # Try user-specific key first
        if user_id:
            from ..database import User
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if user and user.google_maps_api_key:
                    return user.google_maps_api_key
        
        # Fall back to global setting
        return self.get_setting('GOOGLE_MAPS_API_KEY')
    
    def get_spreadsheet_id(self, user_id: int) -> Optional[str]:
        """
        Get spreadsheet ID for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Spreadsheet ID or None
        """
        from ..database import User
        with db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                return user.spreadsheet_id
        
        return None
    
    def get_target_user_name(self, user_id: int) -> str:
        """
        Get target user name for a user
        
        Args:
            user_id: User ID
        
        Returns:
            User name
        """
        from ..database import User
        with db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                return user.name
        
        return "UNKNOWN"


# Global instance
settings_storage = SettingsStorage()
