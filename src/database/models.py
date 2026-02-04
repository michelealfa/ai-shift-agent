"""
SQLAlchemy ORM Models for AI Shift Agent
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean, Column, Integer, String, Text, DateTime, Date, 
    ForeignKey, Index, TIMESTAMP, JSON
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User account with authentication and configuration"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    avatar_url = Column(Text, nullable=True)
    spreadsheet_id = Column(String(255), nullable=True)
    gemini_api_key = Column(String(255), nullable=True)
    google_maps_api_key = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    shifts = relationship("Shift", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.display_name}', active={self.is_active})>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,  # Keep as integer
            "name": self.name,
            "display_name": self.display_name,
            "api_key": self.api_key,
            "avatar": self.avatar_url,
            "avatar_url": self.avatar_url,  # Both for compatibility
            "spreadsheet_id": self.spreadsheet_id,
            "gemini_api_key": self.gemini_api_key,
            "google_maps_api_key": self.google_maps_api_key,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
        }


class SystemSetting(Base):
    """Global system configuration key-value pairs"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SystemSetting(key='{self.key}', value='{self.value[:50]}...')>"


class Prompt(Base):
    """AI prompt templates for various tasks"""
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    template = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Prompt(name='{self.name}', active={self.is_active})>"


class Shift(Base):
    """User shift data with sync status"""
    __tablename__ = "shifts"
    __table_args__ = (
        Index('idx_shifts_user_date', 'user_id', 'shift_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shift_date = Column(Date, nullable=False, index=True)
    slot_1 = Column(String(50), nullable=True)
    slot_2 = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    source = Column(String(50), default="ocr")  # 'ocr', 'manual', 'sheets'
    synced_to_sheets = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="shifts")

    def __repr__(self):
        return f"<Shift(user_id={self.user_id}, date={self.shift_date}, slot_1='{self.slot_1}')>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date": self.shift_date.isoformat() if self.shift_date else None,
            "slot_1": self.slot_1,
            "slot_2": self.slot_2,
            "notes": self.notes,
            "source": self.source,
            "synced": self.synced_to_sheets,
        }


class ActivityLog(Base):
    """Audit trail of all system actions"""
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    details = Column(JSONB, nullable=True)
    level = Column(String(20), default="INFO", index=True)  # 'INFO', 'WARNING', 'ERROR'
    ip_address = Column(INET, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog(action='{self.action}', level='{self.level}', user_id={self.user_id})>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "details": self.details,
            "level": self.level,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Session(Base):
    """Web session storage"""
    __tablename__ = "sessions"

    id = Column(String(255), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    data = Column(JSONB, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session(id='{self.id}', user_id={self.user_id})>"
