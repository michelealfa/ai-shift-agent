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
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    tier = Column(String(50), default="free")  # free, pro, team
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    shifts = relationship("Shift", back_populates="user", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="user", cascade="all, delete-orphan")
    commute_profiles = relationship("CommuteProfile", back_populates="user", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', tier={self.tier})>"

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "display_name": self.display_name,
            "tier": self.tier,
            "avatar": self.avatar_url,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class APIKey(Base):
    """User API Keys for multi-tenant access"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    label = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    quota_limit = Column(Integer, default=1000)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="api_keys")


class Shift(Base):
    """User shift data"""
    __tablename__ = "shifts"
    __table_args__ = (
        Index('idx_shifts_user_date', 'user_id', 'shift_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shift_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(50), nullable=True)
    end_time = Column(String(50), nullable=True)
    source = Column(String(50), default="manual")  # 'ocr', 'manual'
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="shifts")
    versions = relationship("ShiftVersion", back_populates="shift", cascade="all, delete-orphan")
    traffic_snapshots = relationship("TrafficSnapshot", back_populates="shift")


class ShiftVersion(Base):
    """Versioning for shift changes"""
    __tablename__ = "shift_versions"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False)
    payload = Column(JSONB, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())

    shift = relationship("Shift", back_populates="versions")


class Location(Base):
    """User-defined locations (home, work, etc)"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(255), nullable=False)
    address = Column(String(500), nullable=True)
    lat = Column(Integer, nullable=True)  # Store as integer (microdegrees) or float
    lng = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="locations")


class CommuteProfile(Base):
    """Definitions of frequent commutes"""
    __tablename__ = "commute_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    origin_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    destination_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    transport_type = Column(String(50), default="car")
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="commute_profiles")


class TrafficSnapshot(Base):
    """Snapshot of traffic data for a shift"""
    __tablename__ = "traffic_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    commute_profile_id = Column(Integer, ForeignKey("commute_profiles.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)
    departure_time = Column(DateTime, nullable=False)
    travel_time_minutes = Column(Integer, nullable=False)
    confidence = Column(Integer, default=100)
    created_at = Column(DateTime, default=func.now())

    shift = relationship("Shift", back_populates="traffic_snapshots")


class ConfigVersion(Base):
    """System configuration versions (prompts, thresholds)"""
    __tablename__ = "config_versions"

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String(50), nullable=False, index=True)  # vision, nlp, traffic
    version = Column(Integer, nullable=False)
    payload = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class AgentRun(Base):
    """Tracking of AI Agent reasoning and actions"""
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    input = Column(Text, nullable=False)
    output = Column(Text, nullable=True)
    reasoning = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="agent_runs")


class ActivityLog(Base):
    """Audit trail of all system actions"""
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    details = Column(JSONB, nullable=True)
    level = Column(String(20), default="INFO", index=True)
    ip_address = Column(INET, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)

    user = relationship("User", back_populates="activity_logs")
