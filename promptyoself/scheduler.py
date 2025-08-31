"""
Scheduler logic for promptyoself plugin.
Handles cron calculations, prompt execution, and background scheduling.
"""

import time
from datetime import datetime, timedelta
from croniter import croniter
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Import our structured logging with proper path handling
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from .logging_config import get_logger, PerformanceTimer
    from .db import get_due_schedules, update_schedule, UnifiedReminder, CLIReminderAdapter
    from .letta_api import send_prompt_to_agent
except ImportError:
    try:
        from logging_config import get_logger, PerformanceTimer
        from db import get_due_schedules, update_schedule, UnifiedReminder, CLIReminderAdapter
        from letta_api import send_prompt_to_agent
    except ImportError:
        # If still failing, use basic logging
        import logging
        logging.basicConfig(level=logging.INFO)
        
        def get_logger(name):
            return logging.getLogger(name)
        
        class PerformanceTimer:
            def __init__(self, operation):
                self.operation = operation
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        
        # Import other modules by absolute path
        import importlib.util
        
        # Import db
        db_path = os.path.join(current_dir, 'db.py')
        spec = importlib.util.spec_from_file_location("db", db_path)
        db = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(db)
        get_due_schedules, update_schedule, PromptSchedule = db.get_due_schedules, db.update_schedule, db.PromptSchedule
        
        # Import letta_api
        letta_api_path = os.path.join(current_dir, 'letta_api.py')
        spec = importlib.util.spec_from_file_location("letta_api", letta_api_path)
        letta_api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(letta_api)
        send_prompt_to_agent = letta_api.send_prompt_to_agent

logger = get_logger(__name__)

def calculate_next_run(cron_expr: str, base_time: Optional[datetime] = None) -> datetime:
    """Calculate next run time from cron expression."""
    if base_time is None:
        base_time = datetime.utcnow()
    
    cron = croniter(cron_expr, base_time)
    return cron.get_next(datetime)

def calculate_next_run_for_schedule(unified_reminder: UnifiedReminder) -> Optional[datetime]:
    """Calculate next run time for a unified reminder based on its type."""
    if unified_reminder.schedule_type == "once":
        # One-time reminders don't have a next run
        return None
    elif unified_reminder.schedule_type == "cron":
        return calculate_next_run(unified_reminder.schedule_value)
    elif unified_reminder.schedule_type == "interval":
        # Parse interval (e.g., "60s", "5m", "1h")
        interval_str = unified_reminder.schedule_value
        if interval_str.endswith('s'):
            seconds = int(interval_str[:-1])
        elif interval_str.endswith('m'):
            seconds = int(interval_str[:-1]) * 60
        elif interval_str.endswith('h'):
            seconds = int(interval_str[:-1]) * 3600
        else:
            seconds = int(interval_str)  # Default to seconds
        
        return datetime.utcnow() + timedelta(seconds=seconds)
    else:
        raise ValueError(f"Unknown schedule type: {unified_reminder.schedule_type}")

def execute_due_prompts() -> List[Dict[str, Any]]:
    """Execute all due prompts and update their schedules."""
    start_time = time.time()
    
    try:
        due_schedules = get_due_schedules()
        executed = []
        
        logger.info("Starting scheduled prompt execution", extra={
            'operation_type': 'scheduler',
            'scheduler_event': 'execution_start',
            'due_schedules_count': len(due_schedules)
        })
        
        if not due_schedules:
            logger.debug("No due schedules found", extra={
                'operation_type': 'scheduler',
                'scheduler_event': 'no_due_schedules'
            })
            return executed
    
        for unified_reminder in due_schedules:
            schedule_start_time = time.time()
            try:
                logger.info("Executing individual schedule", extra={
                    'operation_type': 'scheduler',
                    'scheduler_event': 'schedule_execution',
                    'reminder_id': unified_reminder.id,
                    'agent_id': unified_reminder.agent_id,
                    'schedule_type': unified_reminder.schedule_type,
                    'repetition_count': unified_reminder.repetition_count,
                    'max_repetitions': unified_reminder.max_repetitions
                })
                
                # Send prompt to agent
                success = send_prompt_to_agent(unified_reminder.agent_id, unified_reminder.message)
                
                # Update schedule
                update_data = {
                    "last_run": datetime.utcnow()
                }
                
                if success:
                    # Increment repetition count (treat None as 0 for newly constructed objects)
                    current_count = unified_reminder.repetition_count or 0
                    new_repetition_count = current_count + 1
                    update_data["repetition_count"] = new_repetition_count
                    
                    # Check if we've reached the maximum repetitions
                    if unified_reminder.max_repetitions is not None and new_repetition_count >= unified_reminder.max_repetitions:
                        # Finite repetition limit reached, deactivate the reminder
                        update_data["active"] = False
                        next_run = None
                        logger.info(f"Reminder {unified_reminder.id} completed {unified_reminder.max_repetitions} repetitions, deactivating")
                    else:
                        # Calculate next run time
                        next_run = calculate_next_run_for_schedule(unified_reminder)
                        if next_run:
                            update_data["next_run"] = next_run
                        else:
                            # One-time reminder, deactivate it
                            update_data["active"] = False
                    
                    executed.append({
                        "id": unified_reminder.id,
                        "agent_id": unified_reminder.agent_id,
                        "delivered": True,
                        "next_run": next_run.isoformat() if next_run else None,
                        "repetition_count": new_repetition_count,
                        "max_repetitions": unified_reminder.max_repetitions,
                        "completed": unified_reminder.max_repetitions is not None and new_repetition_count >= unified_reminder.max_repetitions
                    })
                else:
                    # Failed to deliver, keep the same next_run time for retry
                    executed.append({
                        "id": unified_reminder.id,
                        "agent_id": unified_reminder.agent_id,
                        "delivered": False,
                        "error": "Failed to deliver prompt",
                        "next_run": unified_reminder.next_run.isoformat()
                    })
                
                update_schedule(unified_reminder.id, **update_data)
            
            except Exception as e:
                schedule_duration = time.time() - schedule_start_time
                logger.error("Reminder execution failed", extra={
                    'operation_type': 'scheduler',
                    'scheduler_event': 'reminder_execution_failed',
                    'reminder_id': unified_reminder.id,
                    'agent_id': unified_reminder.agent_id,
                    'duration': schedule_duration,
                    'error': str(e)
                }, exc_info=True)
                
                executed.append({
                    "id": unified_reminder.id,
                    "agent_id": unified_reminder.agent_id,
                    "delivered": False,
                    "error": str(e),
                    "next_run": unified_reminder.next_run.isoformat()
                })
        
        total_duration = time.time() - start_time
        successful_executions = sum(1 for result in executed if result.get('delivered', False))
        failed_executions = len(executed) - successful_executions
        
        logger.info("Scheduled prompt execution completed", extra={
            'operation_type': 'scheduler',
            'scheduler_event': 'execution_completed',
            'total_schedules': len(due_schedules),
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'total_duration': total_duration
        })
        
        return executed
    
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error("Critical error in scheduled prompt execution", extra={
            'operation_type': 'scheduler',
            'scheduler_event': 'execution_critical_error',
            'duration': total_duration,
            'error': str(e)
        }, exc_info=True)
        raise

class PromptScheduler:
    """Background scheduler for executing prompts."""
    
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self.scheduler = None
        self.running = False
    
    def start(self):
        """Start the background scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info(f"Starting prompt scheduler with {self.interval_seconds}s interval")
        
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            func=self._execute_job,
            trigger=IntervalTrigger(seconds=self.interval_seconds),
            id='execute_prompts',
            name='Execute Due Prompts',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.running = True
        logger.info("Prompt scheduler started")
    
    def stop(self):
        """Stop the background scheduler."""
        if not self.running:
            return
        
        logger.info("Stopping prompt scheduler")
        if self.scheduler:
            self.scheduler.shutdown()
        self.running = False
        logger.info("Prompt scheduler stopped")
    
    def _execute_job(self):
        """Internal job execution method."""
        try:
            results = execute_due_prompts()
            if results:
                logger.info(f"Executed {len(results)} prompts")
        except Exception as e:
            logger.error(f"Error in scheduled job: {e}")
    
    def run_loop(self):
        """Run the scheduler in a blocking loop."""
        self.start()
        try:
            logger.info("Scheduler running in loop mode. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()

def run_scheduler_loop(interval_seconds: int = 60):
    """Run the scheduler in a blocking loop."""
    scheduler = PromptScheduler(interval_seconds)
    scheduler.run_loop()