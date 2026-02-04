"""
Database module initialization
"""
from .connection import db_manager, get_db, init_db, close_db
from .models import Base, User, SystemSetting, Prompt, Shift, ActivityLog, Session

__all__ = [
    'db_manager',
    'get_db',
    'init_db',
    'close_db',
    'Base',
    'User',
    'SystemSetting',
    'Prompt',
    'Shift',
    'ActivityLog',
    'Session'
]
