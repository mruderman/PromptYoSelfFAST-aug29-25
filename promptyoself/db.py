import os
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Index, ForeignKey
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import List, Dict, Any, Optional

# Import our structured logging
try:
    from .logging_config import get_logger, PerformanceTimer
except ImportError:
    # Fallback for when running as script
    from logging_config import get_logger, PerformanceTimer

# Initialize logger
logger = get_logger(__name__)

# --- Database Setup ---
Base = declarative_base()

# Global variables for lazy initialization
_engine = None
_SessionLocal = None

def get_db_file():
    """Get database file path, respecting current environment variables."""
    # Default to unified database path for integration
    default_path = "/app/promptyoself/instance/unified.sqlite3"
    if not os.path.exists(os.path.dirname(default_path)):
        # Fallback to local file if Docker path doesn't exist
        default_path = "promptyoself.db"
    return os.environ.get("PROMPTYOSELF_DB", default_path)

def get_engine():
    """Get database engine, creating it if necessary."""
    global _engine
    if _engine is None:
        db_file = get_db_file()
        logger.info("Creating database engine", extra={
            'operation_type': 'database',
            'db_operation': 'create_engine',
            'database_file': db_file
        })
        _engine = create_engine(f"sqlite:///{db_file}")
        logger.debug("Database engine created successfully", extra={
            'operation_type': 'database',
            'database_file': db_file
        })
        
        # Ensure tables are created when engine is first created
        try:
            Base.metadata.create_all(bind=_engine)
            logger.debug("Database tables ensured", extra={
                'operation_type': 'database',
                'db_operation': 'ensure_tables'
            })
        except Exception as e:
            logger.error("Failed to ensure database tables", extra={
                'operation_type': 'database',
                'error': str(e)
            })
    return _engine

def get_session_factory():
    """Get session factory, creating it if necessary."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

# --- Models ---
class UnifiedReminder(Base):
    """Unified reminder model serving both web and CLI interfaces."""
    
    __tablename__ = "unified_reminders"
    
    # Core fields (required for both interfaces)
    id = Column(Integer, primary_key=True)
    message = Column(Text, nullable=False)  # Universal message text
    next_run = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True, index=True)
    
    # Scheduling fields (support both simple and complex scheduling)
    schedule_type = Column(String(50), nullable=True)  # 'once', 'cron', 'interval', 'simple'
    schedule_value = Column(String(200), nullable=True)  # Cron expression, interval, etc.
    recurrence = Column(String(50), nullable=True)  # Simple recurrence for web interface
    
    # Repetition tracking
    max_repetitions = Column(Integer, nullable=True)
    repetition_count = Column(Integer, default=0)
    event_count = Column(Integer, default=0)  # Legacy compatibility
    last_run = Column(DateTime, nullable=True)
    
    # Interface-specific fields
    agent_id = Column(String(100), nullable=True, index=True)  # For CLI interface
    process_name = Column(Text, nullable=True)  # For both interfaces
    
    # Web interface relationships (nullable for CLI-only reminders)
    task_id = Column(Integer, nullable=True)  # References tasks.id when used with web interface
    user_id = Column(Integer, nullable=True)  # References users.id when used with web interface

# Performance indexes for unified reminders
Index('idx_unified_reminders_due', UnifiedReminder.next_run, UnifiedReminder.active)
Index('idx_unified_reminders_agent', UnifiedReminder.agent_id, UnifiedReminder.active)
Index('idx_unified_reminders_task', UnifiedReminder.task_id, UnifiedReminder.active)
Index('idx_unified_reminders_status', UnifiedReminder.status, UnifiedReminder.next_run)

# Legacy PromptSchedule model for backward compatibility during transition
class PromptSchedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True)
    agent_id = Column(String, nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    schedule_type = Column(String, nullable=False)  # 'once', 'cron', or 'interval'
    schedule_value = Column(String, nullable=False)
    next_run = Column(DateTime, nullable=False, index=True)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_run = Column(DateTime, nullable=True)
    max_repetitions = Column(Integer, nullable=True)
    repetition_count = Column(Integer, default=0)

# Legacy indexes
Index('idx_schedules_due', PromptSchedule.next_run, PromptSchedule.active)
Index('idx_schedules_agent_active', PromptSchedule.agent_id, PromptSchedule.active)
Index('idx_schedules_created_at', PromptSchedule.created_at)

# --- CLI Adapter ---
class CLIReminderAdapter:
    """Adapter for CLI interface using Agent structure."""
    
    @staticmethod
    def create_from_cli_args(agent_id, prompt_text, schedule_type, schedule_value, 
                           next_run, max_repetitions=None):
        """Create unified reminder from CLI arguments."""
        return UnifiedReminder(
            message=prompt_text,
            next_run=next_run,
            agent_id=agent_id,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            max_repetitions=max_repetitions,
            process_name='cli_interface'
        )
    
    @staticmethod
    def to_cli_format(unified_reminder):
        """Convert unified reminder to CLI interface format."""
        return {
            'id': unified_reminder.id,
            'agent_id': unified_reminder.agent_id,
            'prompt_text': unified_reminder.message,
            'schedule_type': unified_reminder.schedule_type,
            'schedule_value': unified_reminder.schedule_value,
            'next_run': unified_reminder.next_run.isoformat(),
            'active': unified_reminder.active,
            'created_at': unified_reminder.created_at.isoformat(),
            'last_run': unified_reminder.last_run.isoformat() if unified_reminder.last_run else None,
            'max_repetitions': unified_reminder.max_repetitions,
            'repetition_count': unified_reminder.repetition_count,
        }

def initialize_db():
    """Create all tables in the database."""
    with PerformanceTimer("initialize_database", logger, {'operation_type': 'database'}):
        try:
            logger.info("Initializing database tables", extra={
                'operation_type': 'database',
                'db_operation': 'create_tables'
            })
            Base.metadata.create_all(bind=get_engine())
            logger.info("Database tables initialized successfully", extra={
                'operation_type': 'database',
                'db_operation': 'create_tables',
                'table_count': len(Base.metadata.tables)
            })
        except Exception as e:
            logger.error("Failed to initialize database tables", extra={
                'operation_type': 'database',
                'db_operation': 'create_tables',
                'error': str(e)
            }, exc_info=True)
            raise

def get_session() -> Session:
    """Get a new database session."""
    SessionLocal = get_session_factory()
    return SessionLocal()

def reset_db_connection():
    """Reset database connection for testing."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None

def cleanup_old_schedules(days_old: int = 30) -> int:
    """Clean up old completed/cancelled schedules older than specified days.
    
    Args:
        days_old: Number of days after which to clean up old schedules
        
    Returns:
        Number of schedules deleted
    """
    session = get_session()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Delete old inactive unified reminders (CLI only to avoid affecting web)
        result = session.query(UnifiedReminder).filter(
            UnifiedReminder.active == False,
            UnifiedReminder.created_at < cutoff_date,
            UnifiedReminder.agent_id.isnot(None)  # Only clean up CLI reminders
        ).delete()
        
        session.commit()
        return result
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_database_stats() -> Dict[str, Any]:
    """Get database statistics for monitoring."""
    session = get_session()
    try:
        # Stats for unified reminders
        total_reminders = session.query(UnifiedReminder).count()
        active_reminders = session.query(UnifiedReminder).filter(UnifiedReminder.active == True).count()
        inactive_reminders = total_reminders - active_reminders
        
        # CLI vs Web breakdown
        cli_reminders = session.query(UnifiedReminder).filter(UnifiedReminder.agent_id.isnot(None)).count()
        web_reminders = session.query(UnifiedReminder).filter(UnifiedReminder.task_id.isnot(None)).count()
        
        # Get oldest and newest reminders
        oldest = session.query(UnifiedReminder.created_at).order_by(UnifiedReminder.created_at.asc()).first()
        newest = session.query(UnifiedReminder.created_at).order_by(UnifiedReminder.created_at.desc()).first()
        
        db_file = get_db_file()
        db_size = os.path.getsize(db_file) if os.path.exists(db_file) else 0
        
        return {
            "total_reminders": total_reminders,
            "active_reminders": active_reminders,
            "inactive_reminders": inactive_reminders,
            "cli_reminders": cli_reminders,
            "web_reminders": web_reminders,
            "oldest_reminder": oldest[0] if oldest else None,
            "newest_reminder": newest[0] if newest else None,
            "database_file": db_file,
            "database_size_bytes": db_size,
            "database_size_mb": round(db_size / 1024 / 1024, 2)
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()

# --- CRUD Operations ---

def add_schedule(agent_id: str, prompt_text: str, schedule_type: str, schedule_value: str, next_run: datetime, max_repetitions: Optional[int] = None) -> int:
    """Add a new schedule to the database using unified schema."""
    start_time = time.time()
    session = get_session()
    try:
        logger.debug("Creating new unified reminder", extra={
            'operation_type': 'database',
            'db_operation': 'insert',
            'table': 'unified_reminders',
            'agent_id': agent_id,
            'schedule_type': schedule_type,
            'schedule_value': schedule_value,
            'next_run': next_run.isoformat(),
            'max_repetitions': max_repetitions
        })
        
        # Create using CLI adapter
        unified_reminder = CLIReminderAdapter.create_from_cli_args(
            agent_id=agent_id,
            prompt_text=prompt_text,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            next_run=next_run,
            max_repetitions=max_repetitions
        )
        
        session.add(unified_reminder)
        session.commit()
        session.refresh(unified_reminder)
        
        duration = time.time() - start_time
        logger.info("Unified reminder created successfully", extra={
            'operation_type': 'database',
            'db_operation': 'insert',
            'table': 'unified_reminders',
            'reminder_id': unified_reminder.id,
            'agent_id': agent_id,
            'schedule_type': schedule_type,
            'duration': duration,
            'affected_rows': 1
        })
        
        return unified_reminder.id
    except Exception as e:
        session.rollback()
        duration = time.time() - start_time
        logger.error("Failed to create unified reminder", extra={
            'operation_type': 'database',
            'db_operation': 'insert',
            'table': 'unified_reminders',
            'agent_id': agent_id,
            'schedule_type': schedule_type,
            'duration': duration,
            'error': str(e)
        }, exc_info=True)
        raise
    finally:
        session.close()

def list_schedules(agent_id: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
    """List schedules with optional filtering using unified schema."""
    start_time = time.time()
    session = get_session()
    try:
        logger.debug("Querying unified reminders", extra={
            'operation_type': 'database',
            'db_operation': 'select',
            'table': 'unified_reminders',
            'agent_id': agent_id,
            'active_only': active_only
        })
        
        # Query unified reminders with CLI filter (agent_id is not null)
        query = session.query(UnifiedReminder).filter(
            UnifiedReminder.agent_id.isnot(None)  # CLI interface filter
        )
        if agent_id:
            query = query.filter(UnifiedReminder.agent_id == agent_id)
        if active_only:
            query = query.filter(UnifiedReminder.active == True)
        
        unified_reminders = query.order_by(UnifiedReminder.next_run).all()
        
        duration = time.time() - start_time
        logger.info("Unified reminders retrieved successfully", extra={
            'operation_type': 'database',
            'db_operation': 'select',
            'table': 'unified_reminders',
            'agent_id': agent_id,
            'active_only': active_only,
            'result_count': len(unified_reminders),
            'duration': duration
        })
        
        # Convert to CLI format using adapter
        return [
            CLIReminderAdapter.to_cli_format(reminder)
            for reminder in unified_reminders
        ]
    except Exception as e:
        duration = time.time() - start_time
        logger.error("Failed to retrieve unified reminders", extra={
            'operation_type': 'database',
            'db_operation': 'select',
            'table': 'unified_reminders',
            'agent_id': agent_id,
            'active_only': active_only,
            'duration': duration,
            'error': str(e)
        }, exc_info=True)
        raise
    finally:
        session.close()

def get_schedule(schedule_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific schedule by its ID using unified schema."""
    session = get_session()
    try:
        unified_reminder = session.query(UnifiedReminder).filter(
            UnifiedReminder.id == schedule_id,
            UnifiedReminder.agent_id.isnot(None)  # Ensure it's a CLI reminder
        ).first()
        if unified_reminder:
            return CLIReminderAdapter.to_cli_format(unified_reminder)
        return None
    finally:
        session.close()

def update_schedule(schedule_id: int, **kwargs) -> bool:
    """Update a schedule's attributes using unified schema."""
    session = get_session()
    try:
        unified_reminder = session.query(UnifiedReminder).filter(
            UnifiedReminder.id == schedule_id,
            UnifiedReminder.agent_id.isnot(None)  # Ensure it's a CLI reminder
        ).first()
        if not unified_reminder:
            return False
        
        # Map CLI field names to unified field names
        field_mapping = {
            'prompt_text': 'message',
            'active': 'active',
            'next_run': 'next_run',
            'last_run': 'last_run',
            'schedule_type': 'schedule_type',
            'schedule_value': 'schedule_value',
            'max_repetitions': 'max_repetitions',
            'repetition_count': 'repetition_count'
        }
        
        for key, value in kwargs.items():
            unified_field = field_mapping.get(key, key)
            setattr(unified_reminder, unified_field, value)
            
        session.commit()
        return True
    finally:
        session.close()

def cancel_schedule(schedule_id: int) -> bool:
    """Cancel (deactivate) a schedule."""
    return update_schedule(schedule_id, active=False)

def get_due_schedules() -> List[UnifiedReminder]:
    """Get all active schedules that are due to run using unified schema."""
    start_time = time.time()
    session = get_session()
    try:
        now = datetime.utcnow()
        logger.debug("Querying due unified reminders", extra={
            'operation_type': 'database',
            'db_operation': 'select',
            'table': 'unified_reminders',
            'query_time': now.isoformat(),
            'filter': 'active=True AND next_run <= now AND agent_id IS NOT NULL'
        })
        
        # Get due reminders for both CLI and web interfaces
        unified_reminders = session.query(UnifiedReminder).filter(
            UnifiedReminder.active == True,
            UnifiedReminder.next_run <= now
        ).all()
        
        duration = time.time() - start_time
        logger.info("Due unified reminders retrieved", extra={
            'operation_type': 'database',
            'db_operation': 'select',
            'table': 'unified_reminders',
            'query_time': now.isoformat(),
            'due_reminders_count': len(unified_reminders),
            'duration': duration
        })
        
        if unified_reminders:
            logger.debug("Found due unified reminders", extra={
                'operation_type': 'database',
                'due_reminder_ids': [r.id for r in unified_reminders],
                'due_reminder_agents': [r.agent_id for r in unified_reminders if r.agent_id],
                'due_reminder_tasks': [r.task_id for r in unified_reminders if r.task_id]
            })
        
        return unified_reminders
    except Exception as e:
        duration = time.time() - start_time
        logger.error("Failed to retrieve due unified reminders", extra={
            'operation_type': 'database',
            'db_operation': 'select',
            'table': 'unified_reminders',
            'duration': duration,
            'error': str(e)
        }, exc_info=True)
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("Initializing database...")
    initialize_db()
    print("Database initialized.")