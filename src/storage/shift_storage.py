"""
Database-backed shift storage
Replaces JSON file storage with PostgreSQL
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import db_manager, Shift, User

logger = logging.getLogger(__name__)


class ShiftStorage:
    """Manages shift data in PostgreSQL"""
    
    def __init__(self):
        pass
    
    def get_user_shifts(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Shift]:
        """
        Get shifts for a user within a date range
        
        Args:
            user_id: User ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        
        Returns:
            List of Shift objects
        """
        with db_manager.get_session() as session:
            query = session.query(Shift).filter(Shift.user_id == user_id)
            
            if start_date:
                query = query.filter(Shift.shift_date >= start_date)
            
            if end_date:
                query = query.filter(Shift.shift_date <= end_date)
            
            shifts = query.order_by(Shift.shift_date).all()
            
            # Detach from session
            session.expunge_all()
            
            return shifts
    
    def get_current_week_shifts(self, user_id: int) -> List[Shift]:
        """
        Get shifts for the current week (Monday to Sunday)
        
        Args:
            user_id: User ID
        
        Returns:
            List of Shift objects for current week
        """
        today = date.today()
        
        # Get Monday of current week
        monday = today - timedelta(days=today.weekday())
        
        # Get Sunday of current week
        sunday = monday + timedelta(days=6)
        
        return self.get_user_shifts(user_id, monday, sunday)
    
    def get_shift_by_date(self, user_id: int, shift_date: date) -> Optional[Shift]:
        """
        Get a specific shift by date
        
        Args:
            user_id: User ID
            shift_date: Date of the shift
        
        Returns:
            Shift object or None
        """
        with db_manager.get_session() as session:
            shift = session.query(Shift).filter_by(
                user_id=user_id,
                shift_date=shift_date
            ).first()
            
            if shift:
                session.expunge(shift)
            
            return shift
    
    ) -> List[Shift]:
        """
        Save multiple shifts at once
        
        Args:
            user_id: User ID
            shifts_data: List of dicts with 'date', 'slot_1', 'slot_2', 'notes'
            source: Source of data
        
        Returns:
            List of saved Shift objects
        """
        saved_shifts = []
        
        for shift_data in shifts_data:
            try:
                # Parse date
                if isinstance(shift_data.get('date'), str):
                    shift_date = datetime.strptime(shift_data['date'], '%Y-%m-%d').date()
                else:
                    shift_date = shift_data['date']
                
                # Save shift
                shift = self.save_shift(
                    user_id=user_id,
                    shift_date=shift_date,
                    slot_1=shift_data.get('slot_1'),
                    slot_2=shift_data.get('slot_2'),
                    notes=shift_data.get('notes'),
                    source=source
                )
                
                saved_shifts.append(shift)
                
            except Exception as e:
                logger.error(f"Failed to save shift: {shift_data}, error: {e}")
        
        return saved_shifts
    
    def delete_shift(self, user_id: int, shift_date: date) -> bool:
        """
        Delete a shift
        
        Args:
            user_id: User ID
            shift_date: Date of the shift
        
        Returns:
            True if deleted, False if not found
        """
        with db_manager.get_session() as session:
            shift = session.query(Shift).filter_by(
                user_id=user_id,
                shift_date=shift_date
            ).first()
            
            if shift:
                session.delete(shift)
                session.commit()
                return True
            
            return False
    
        return saved_shifts


# Global instance
shift_storage = ShiftStorage()
