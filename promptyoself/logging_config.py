"""
Enhanced logging configuration for promptyoself plugin.
Provides centralized logging setup with structured output, rotation, and filtering.
"""

import os
import sys
import time
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs with additional context."""
    
    def __init__(self, include_context: bool = True):
        super().__init__()
        self.include_context = include_context
        self.hostname = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry: Dict[str, Any] = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add context if enabled
        if self.include_context:
            log_entry.update({
                'hostname': self.hostname,
                'process_id': str(os.getpid()),
                'thread_id': str(record.thread) if record.thread else None,
                'module': record.module,
                'function': record.funcName,
                'line': str(record.lineno),
            })
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add any extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'message', 'exc_info', 'exc_text', 
                          'stack_info', 'getMessage'}:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry['extra'] = extra_fields
        
        return json.dumps(log_entry, default=str)


class PromptyoselfLogFilter(logging.Filter):
    """Custom filter to add promptyoself-specific context to log records."""
    
    def __init__(self, component: str = "promptyoself"):
        super().__init__()
        self.component = component
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add component identifier
        record.component = self.component
        
        # Add performance timing if available
        if hasattr(record, 'start_time'):
            record.duration = time.time() - record.start_time
        
        return True


class LoggerConfig:
    """Centralized logging configuration for promptyoself."""
    
    def __init__(self, 
                 log_dir: Optional[str] = None,
                 log_level: str = "INFO",
                 enable_console: bool = True,
                 enable_file: bool = True,
                 enable_structured: bool = False,
                 max_bytes: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 component: str = "promptyoself"):
        
        self.log_dir = Path(log_dir) if log_dir else Path(".")
        self.log_level = getattr(logging, log_level.upper())
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_structured = enable_structured
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.component = component
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure the logging system."""
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create custom filter
        log_filter = PromptyoselfLogFilter(self.component)
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            
            if self.enable_structured:
                console_formatter = StructuredFormatter(include_context=False)
            else:
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            console_handler.setFormatter(console_formatter)
            console_handler.addFilter(log_filter)
            root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if self.enable_file:
            log_file = self.log_dir / f"{self.component}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            file_handler.setLevel(self.log_level)
            
            if self.enable_structured:
                file_formatter = StructuredFormatter(include_context=True)
            else:
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
                )
            
            file_handler.setFormatter(file_formatter)
            file_handler.addFilter(log_filter)
            root_logger.addHandler(file_handler)
        
        # Error file handler (separate file for errors)
        error_log_file = self.log_dir / f"{self.component}_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        error_handler.setLevel(logging.ERROR)
        
        if self.enable_structured:
            error_formatter = StructuredFormatter(include_context=True)
        else:
            error_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
            )
        
        error_handler.setFormatter(error_formatter)
        error_handler.addFilter(log_filter)
        root_logger.addHandler(error_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name."""
        return logging.getLogger(name)
    
    def log_performance(self, logger: logging.Logger, operation: str, start_time: float, 
                       extra_context: Optional[Dict[str, Any]] = None):
        """Log performance metrics for an operation."""
        import time
        duration = time.time() - start_time
        
        context = {
            'operation': operation,
            'duration': duration,
            'start_time': start_time
        }
        
        if extra_context:
            context.update(extra_context)
        
        logger.info(f"Operation '{operation}' completed in {duration:.3f}s", 
                   extra=context)
    
    def log_database_operation(self, logger: logging.Logger, operation: str, 
                             table: str, affected_rows: int = 0, 
                             extra_context: Optional[Dict[str, Any]] = None):
        """Log database operations with structured context."""
        context = {
            'operation_type': 'database',
            'db_operation': operation,
            'table': table,
            'affected_rows': affected_rows
        }
        
        if extra_context:
            context.update(extra_context)
        
        logger.info(f"Database {operation} on {table} (affected: {affected_rows})", 
                   extra=context)
    
    def log_letta_operation(self, logger: logging.Logger, operation: str, 
                           agent_id: str, success: bool, 
                           extra_context: Optional[Dict[str, Any]] = None):
        """Log Letta API operations with structured context."""
        context = {
            'operation_type': 'letta_api',
            'letta_operation': operation,
            'agent_id': agent_id,
            'success': success
        }
        
        if extra_context:
            context.update(extra_context)
        
        level = logging.INFO if success else logging.ERROR
        status = "succeeded" if success else "failed"
        logger.log(level, f"Letta {operation} for agent {agent_id} {status}", 
                   extra=context)
    
    def log_scheduler_event(self, logger: logging.Logger, event_type: str, 
                           schedule_id: Optional[int] = None, 
                           extra_context: Optional[Dict[str, Any]] = None):
        """Log scheduler events with structured context."""
        context = {
            'operation_type': 'scheduler',
            'scheduler_event': event_type,
            'schedule_id': schedule_id
        }
        
        if extra_context:
            context.update(extra_context)
        
        logger.info(f"Scheduler event: {event_type} (schedule: {schedule_id})", 
                   extra=context)


# Global logger instance
_logger_config: Optional[LoggerConfig] = None


def configure_logging(log_dir: Optional[str] = None,
                     log_level: str = "INFO",
                     enable_console: bool = True,
                     enable_file: bool = True,
                     enable_structured: bool = False,
                     component: str = "promptyoself") -> LoggerConfig:
    """Configure logging for the promptyoself plugin."""
    global _logger_config
    
    # Get configuration from environment variables
    log_dir = log_dir or os.getenv("PROMPTYOSELF_LOG_DIR", ".")
    log_level = os.getenv("PROMPTYOSELF_LOG_LEVEL", log_level)
    enable_console = os.getenv("PROMPTYOSELF_LOG_CONSOLE", "true").lower() == "true"
    enable_file = os.getenv("PROMPTYOSELF_LOG_FILE", "true").lower() == "true"
    enable_structured = os.getenv("PROMPTYOSELF_LOG_STRUCTURED", "false").lower() == "true"
    
    _logger_config = LoggerConfig(
        log_dir=log_dir,
        log_level=log_level,
        enable_console=enable_console,
        enable_file=enable_file,
        enable_structured=enable_structured,
        component=component
    )
    
    return _logger_config


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    if _logger_config is None:
        configure_logging()
    
    return _logger_config.get_logger(name)


def log_performance(operation: str, start_time: float, 
                   extra_context: Optional[Dict[str, Any]] = None):
    """Convenience function to log performance metrics."""
    if _logger_config is None:
        configure_logging()
    
    logger = get_logger(__name__)
    _logger_config.log_performance(logger, operation, start_time, extra_context)


def log_database_operation(operation: str, table: str, affected_rows: int = 0, 
                          extra_context: Optional[Dict[str, Any]] = None):
    """Convenience function to log database operations."""
    if _logger_config is None:
        configure_logging()
    
    logger = get_logger(__name__)
    _logger_config.log_database_operation(logger, operation, table, affected_rows, extra_context)


def log_letta_operation(operation: str, agent_id: str, success: bool, 
                       extra_context: Optional[Dict[str, Any]] = None):
    """Convenience function to log Letta operations."""
    if _logger_config is None:
        configure_logging()
    
    logger = get_logger(__name__)
    _logger_config.log_letta_operation(logger, operation, agent_id, success, extra_context)


def log_scheduler_event(event_type: str, schedule_id: Optional[int] = None, 
                       extra_context: Optional[Dict[str, Any]] = None):
    """Convenience function to log scheduler events."""
    if _logger_config is None:
        configure_logging()
    
    logger = get_logger(__name__)
    _logger_config.log_scheduler_event(logger, event_type, schedule_id, extra_context)


# Context managers for performance logging
class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, operation: str, logger: Optional[logging.Logger] = None, 
                 extra_context: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.logger = logger or get_logger(__name__)
        self.extra_context = extra_context or {}
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.debug(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            if _logger_config:
                _logger_config.log_performance(self.logger, self.operation, 
                                             self.start_time, self.extra_context)
            
            if exc_type is not None:
                self.logger.error(f"Operation '{self.operation}' failed: {exc_val}")


# Initialization
def init_logging():
    """Initialize logging on module import."""
    if _logger_config is None:
        configure_logging()


# Initialize logging when module is imported
init_logging()


if __name__ == "__main__":
    # Test the logging configuration
    import time
    
    # Test different log levels
    logger = get_logger(__name__)
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # Test performance logging
    with PerformanceTimer("test_operation", logger, {"test": "context"}):
        time.sleep(0.1)
    
    # Test structured logging functions
    log_database_operation("SELECT", "schedules", 5, {"query": "SELECT * FROM schedules"})
    log_letta_operation("send_prompt", "agent-123", True, {"prompt": "Hello"})
    log_scheduler_event("schedule_executed", 456, {"result": "success"})
    
    print("Logging test completed. Check the log files.")