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
from ..storage.sheets_client import SheetsClient

logger = logging.getLogger(__name__)


class ShiftStorage:
    """Manages shift data in PostgreSQL with Google Sheets sync"""
    
    def __init__(self):
        self.sheets_client = None
    
    def _get_sheets_client(self, user: User) -> SheetsClient:
        """Get or create sheets client for user"""
        if not self.sheets_client or self.sheets_client.spreadsheet_id != user.spreadsheet_id:
            spreadsheet_id = user.spreadsheet_id or ""
            self.sheets_client = SheetsClient(spreadsheet_id=spreadsheet_id)
        return self.sheets_client
    
    def save_shift(
        self, 
        user_id: int, 
        shift_date: date, 
        slot_1: Optional[str] = None,
        slot_2: Optional[str] = None,
        notes: Optional[str] = None,
        source: str = "ocr",
        sync_to_sheets: bool = True
    ) -> Shift:
        """
        Save or update a shift
        
        Args:
            user_id: User ID
            shift_date: Date of the shift
            slot_1: First time slot
            slot_2: Second time slot
            notes: Additional notes
            source: Source of data ('ocr', 'manual', 'sheets')
            sync_to_sheets: Whether to sync to Google Sheets
        
        Returns:
            Shift object
        """
        with db_manager.get_session() as session:
            # Check if shift exists
            existing = session.query(Shift).filter_by(
                user_id=user_id,
                shift_date=shift_date
            ).first()
            
            if existing:
                # Update existing
                existing.slot_1 = slot_1
                existing.slot_2 = slot_2
                existing.notes = notes
                existing.source = source
                existing.synced_to_sheets = False  # Mark as needing sync
                shift = existing
            else:
                # Create new
                shift = Shift(
                    user_id=user_id,
                    shift_date=shift_date,
                    slot_1=slot_1,
                    slot_2=slot_2,
                    notes=notes,
                    source=source,
                    synced_to_sheets=False
                )
                session.add(shift)
            
            session.commit()
            session.refresh(shift)
            
            # Sync to Google Sheets if requested
            if sync_to_sheets:
                self._sync_shift_to_sheets(session, shift)
            
            return shift
    
    def _sync_shift_to_sheets(self, session: Session, shift: Shift):
        """Sync a shift to Google Sheets"""
        try:
            # Get user
            user = session.query(User).filter_by(id=shift.user_id).first()
            if not user:
                logger.error(f"User not found for shift: {shift.id}")
                return
            
            # Get sheets client
            sheets_client = self._get_sheets_client(user)
            
            # Update shift in sheets
            sheets_client.update_shift(
                target_date=shift.shift_date.strftime("%Y-%m-%d"),
                target_user=user.name,
                new_values={
                    "slot_1": shift.slot_1 or "",
                    "slot_2": shift.slot_2 or "",
                    "notes": shift.notes or ""
                }
            )
            
            # Mark as synced
            shift.synced_to_sheets = True
            session.commit()
            
            logger.info(f"Synced shift {shift.id} to Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to sync shift to Sheets: {e}")
    
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
    
    def bulk_save_shifts(
        self,
        user_id: int,
        shifts_data: List[Dict],
        source: str = "ocr",
        sync_to_sheets: bool = True
    ) -> List[Shift]:
        """
        Save multiple shifts at once
        
        Args:
            user_id: User ID
            shifts_data: List of dicts with 'date', 'slot_1', 'slot_2', 'notes'
            source: Source of data
            sync_to_sheets: Whether to sync to Google Sheets
        
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
                    source=source,
                    sync_to_sheets=sync_to_sheets
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
    
    def sync_from_sheets(self, user_id: int) -> int:
        """
        Pull shifts from Google Sheets and save to database
        
        Args:
            user_id: User ID
        
        Returns:
            Number of shifts synced
        """
        with db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                logger.error(f"User not found: {user_id}")
                return 0
            
            try:
                # Get sheets client
                sheets_client = self._get_sheets_client(user)
                
                # Get data from sheets
                sheet_data = sheets_client.get_latest_sheet_data()
                
                if not sheet_data:
                    logger.warning("No data from Google Sheets")
                    return 0
                
                synced_count = 0
                
                # Parse sheet data (assuming format: [date, day, user, slot1, slot2, notes])
                for row in sheet_data[1:]:  # Skip header
                    if len(row) < 4:
                        continue
                    
                    # Check if this row is for this user
                    if len(row) > 2 and row[2] != user.name:
                        continue
                    
                    try:
                        # Parse date
                        shift_date = datetime.strptime(row[0], '%Y-%m-%d').date()
                        
                        # Save shift
                        self.save_shift(
                            user_id=user_id,
                            shift_date=shift_date,
                            slot_1=row[3] if len(row) > 3 else None,
                            slot_2=row[4] if len(row) > 4 else None,
                            notes=row[5] if len(row) > 5 else None,
                            source='sheets',
                            sync_to_sheets=False  # Already from sheets
                        )
                        
                        synced_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to parse row: {row}, error: {e}")
                
                logger.info(f"Synced {synced_count} shifts from Google Sheets")
                return synced_count
                
            except Exception as e:
                logger.error(f"Failed to sync from Sheets: {e}")
                return 0


# Global instance
shift_storage = ShiftStorage()
