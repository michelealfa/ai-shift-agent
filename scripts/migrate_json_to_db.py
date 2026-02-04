#!/usr/bin/env python3
"""
Migration script to transfer data from JSON files to PostgreSQL database
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import db_manager, User, SystemSetting, Shift
from src.config.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_users():
    """Migrate users from config/users.json to database"""
    users_file = Path("config/users.json")
    
    if not users_file.exists():
        logger.warning(f"Users file not found: {users_file}")
        return 0
    
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        migrated = 0
        with db_manager.get_session() as session:
            for user_data in users_data:
                # Check if user already exists
                existing = session.query(User).filter_by(
                    api_key=user_data.get('api_key')
                ).first()
                
                if existing:
                    logger.info(f"User already exists: {user_data.get('display_name')}")
                    continue
                
                # Create new user
                user = User(
                    name=user_data.get('name', user_data.get('display_name')),
                    display_name=user_data.get('display_name'),
                    api_key=user_data.get('api_key'),
                    avatar_url=user_data.get('avatar'),
                    is_active=True,
                    is_admin=False
                )
                
                session.add(user)
                migrated += 1
                logger.info(f"Migrated user: {user.display_name}")
            
            session.commit()
        
        logger.info(f"✅ Migrated {migrated} users from JSON to database")
        return migrated
        
    except Exception as e:
        logger.error(f"❌ Error migrating users: {e}")
        return 0


def migrate_settings():
    """Migrate settings from config/dynamic_settings.json to database"""
    settings_file = Path("config/dynamic_settings.json")
    
    if not settings_file.exists():
        logger.warning(f"Settings file not found: {settings_file}")
        return 0
    
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        
        migrated = 0
        with db_manager.get_session() as session:
            for key, value in settings_data.items():
                # Check if setting already exists
                existing = session.query(SystemSetting).filter_by(key=key).first()
                
                if existing:
                    # Update existing setting
                    existing.value = str(value)
                    existing.updated_at = datetime.now()
                    logger.info(f"Updated setting: {key}")
                else:
                    # Create new setting
                    setting = SystemSetting(
                        key=key,
                        value=str(value),
                        description=f"Migrated from dynamic_settings.json"
                    )
                    session.add(setting)
                    migrated += 1
                    logger.info(f"Migrated setting: {key}")
            
            session.commit()
        
        logger.info(f"✅ Migrated {migrated} settings from JSON to database")
        return migrated
        
    except Exception as e:
        logger.error(f"❌ Error migrating settings: {e}")
        return 0


def migrate_shift_backups():
    """Migrate shift backups from temp/backups/*.json to database"""
    backups_dir = Path("temp/backups")
    
    if not backups_dir.exists():
        logger.warning(f"Backups directory not found: {backups_dir}")
        return 0
    
    try:
        backup_files = sorted(backups_dir.glob("shifts_*.json"))
        
        if not backup_files:
            logger.warning("No backup files found")
            return 0
        
        # Use the most recent backup
        latest_backup = backup_files[-1]
        logger.info(f"Using latest backup: {latest_backup.name}")
        
        with open(latest_backup, 'r', encoding='utf-8') as f:
            shifts_data = json.load(f)
        
        migrated = 0
        with db_manager.get_session() as session:
            # Get all users for mapping
            users = {u.name: u for u in session.query(User).all()}
            
            for shift_entry in shifts_data:
                user_name = shift_entry.get('user')
                date_str = shift_entry.get('date')
                
                if not user_name or not date_str:
                    continue
                
                # Find user
                user = users.get(user_name)
                if not user:
                    logger.warning(f"User not found: {user_name}")
                    continue
                
                # Parse date
                try:
                    shift_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Invalid date format: {date_str}")
                    continue
                
                # Check if shift already exists
                existing = session.query(Shift).filter_by(
                    user_id=user.id,
                    shift_date=shift_date
                ).first()
                
                if existing:
                    continue
                
                # Create new shift
                shift = Shift(
                    user_id=user.id,
                    shift_date=shift_date,
                    slot_1=shift_entry.get('slot_1'),
                    slot_2=shift_entry.get('slot_2'),
                    notes=shift_entry.get('notes'),
                    source='migration',
                    synced_to_sheets=True  # Assume already synced
                )
                
                session.add(shift)
                migrated += 1
            
            session.commit()
        
        logger.info(f"✅ Migrated {migrated} shifts from backup to database")
        return migrated
        
    except Exception as e:
        logger.error(f"❌ Error migrating shift backups: {e}")
        return 0


def validate_migration():
    """Validate that migration was successful"""
    logger.info("\n📊 Validation Report:")
    
    with db_manager.get_session() as session:
        user_count = session.query(User).count()
        setting_count = session.query(SystemSetting).count()
        shift_count = session.query(Shift).count()
        
        logger.info(f"  Users in database: {user_count}")
        logger.info(f"  Settings in database: {setting_count}")
        logger.info(f"  Shifts in database: {shift_count}")
        
        # Show sample users
        users = session.query(User).limit(5).all()
        logger.info("\n  Sample users:")
        for user in users:
            logger.info(f"    - {user.display_name} (ID: {user.id}, Active: {user.is_active})")
        
        return user_count > 0


def create_backup():
    """Create backup of JSON files before migration"""
    backup_dir = Path("backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_backup = [
        "config/users.json",
        "config/dynamic_settings.json",
    ]
    
    for file_path in files_to_backup:
        src = Path(file_path)
        if src.exists():
            dst = backup_dir / src.name
            dst.write_text(src.read_text())
            logger.info(f"📦 Backed up: {file_path} -> {dst}")
    
    logger.info(f"✅ Backup created: {backup_dir}")
    return backup_dir


def main():
    """Main migration function"""
    logger.info("=" * 60)
    logger.info("🚀 Starting JSON to Database Migration")
    logger.info("=" * 60)
    
    # Initialize database
    try:
        db_manager.initialize()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        logger.error("Make sure PostgreSQL is running and DATABASE_URL is set correctly")
        return 1
    
    # Create tables if they don't exist
    try:
        db_manager.create_tables()
        logger.info("✅ Database tables ready")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        return 1
    
    # Create backup
    logger.info("\n📦 Creating backup of JSON files...")
    backup_dir = create_backup()
    
    # Run migrations
    logger.info("\n🔄 Migrating data...")
    
    users_migrated = migrate_users()
    settings_migrated = migrate_settings()
    shifts_migrated = migrate_shift_backups()
    
    # Validate
    logger.info("\n🔍 Validating migration...")
    if validate_migration():
        logger.info("\n" + "=" * 60)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info(f"  Users migrated: {users_migrated}")
        logger.info(f"  Settings migrated: {settings_migrated}")
        logger.info(f"  Shifts migrated: {shifts_migrated}")
        logger.info(f"  Backup location: {backup_dir}")
        logger.info("\n💡 Next steps:")
        logger.info("  1. Verify data in database")
        logger.info("  2. Update application to use database instead of JSON")
        logger.info("  3. Test all functionality")
        logger.info("  4. Keep JSON backups for 30 days")
        return 0
    else:
        logger.error("\n❌ Migration validation failed!")
        logger.error(f"Backups are available at: {backup_dir}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
