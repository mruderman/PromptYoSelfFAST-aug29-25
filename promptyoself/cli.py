#!/usr/bin/env python3
"""
Promptyoself CLI Plugin

Self-hosted prompt scheduler for Letta agents.
Provides commands to register, list, cancel, and execute scheduled prompts.
"""

import argparse
import json
import sys
import time
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from croniter import croniter

# Try to import logging config from plugin, fall back to basic logging
try:
    from .logging_config import setup_logger
    logger = setup_logger('cli')
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

import sys
import os
# Add the parent directory to path so we can import the modules
current_dir = os.path.dirname(os.path.abspath(__file__))
plugin_dir = os.path.dirname(current_dir)
smcp_dir = os.path.dirname(plugin_dir)
root_dir = os.path.dirname(smcp_dir)
sys.path.insert(0, root_dir)

# Import modules with proper path handling
try:
    # Try absolute import first (works when called from MCP server)
    from promptyoself.db import add_schedule, list_schedules, cancel_schedule
    from promptyoself.scheduler import calculate_next_run, execute_due_prompts, run_scheduler_loop
    from promptyoself.letta_api import test_letta_connection, list_available_agents, validate_agent_exists
except ImportError:
    # Fallback for direct execution - add current directory to path
    import importlib.util
    
    # Import db module
    db_path = os.path.join(current_dir, 'db.py')
    spec = importlib.util.spec_from_file_location("db", db_path)
    db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(db)
    add_schedule, list_schedules, cancel_schedule = db.add_schedule, db.list_schedules, db.cancel_schedule
    
    # Import scheduler module  
    scheduler_path = os.path.join(current_dir, 'scheduler.py')
    spec = importlib.util.spec_from_file_location("scheduler", scheduler_path)
    scheduler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scheduler)
    calculate_next_run, execute_due_prompts, run_scheduler_loop = scheduler.calculate_next_run, scheduler.execute_due_prompts, scheduler.run_scheduler_loop
    
    # Import letta_api module
    letta_api_path = os.path.join(current_dir, 'letta_api.py')
    spec = importlib.util.spec_from_file_location("letta_api", letta_api_path)
    letta_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(letta_api)
    test_letta_connection, list_available_agents, validate_agent_exists = letta_api.test_letta_connection, letta_api.list_available_agents, letta_api.validate_agent_exists


def register_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    """Register a new scheduled prompt for yourself. Exactly one of time, cron, or every must be provided. Make sure to include you own own agent ID."""
    start_time = time.time()
    
    agent_id = args.get("agent_id") or args.get("agent-id")
    prompt = args.get("prompt")
    time_str = args.get("time")
    cron_expr = args.get("cron")
    every_str = args.get("every")
    skip_validation = args.get("skip_validation", False)
    max_repetitions = args.get("max_repetitions") or args.get("max-repetitions")
    start_at = args.get("start_at") or args.get("start-at")
    
    logger.info("Starting prompt registration", extra={
        'operation_type': 'register_prompt',
        'agent_id': agent_id,
        'prompt_length': len(prompt) if prompt else 0,
        'schedule_type': 'once' if time_str else 'cron' if cron_expr else 'interval' if every_str else 'unknown',
        'skip_validation': skip_validation,
        'max_repetitions': max_repetitions
    })
    
    if not agent_id or not prompt:
        error_msg = "Missing required arguments: agent-id and prompt"
        logger.error(error_msg, extra={
            'operation_type': 'register_prompt',
            'error_type': 'missing_arguments',
            'agent_id_provided': bool(agent_id),
            'prompt_provided': bool(prompt)
        })
        return {"error": error_msg}
    
    # Count how many scheduling options are provided
    schedule_options = sum(bool(x) for x in [time_str, cron_expr, every_str])
    if schedule_options == 0:
        error_msg = "Must specify one of --time, --cron, or --every"
        logger.error(error_msg, extra={
            'operation_type': 'register_prompt',
            'error_type': 'no_schedule_option',
            'agent_id': agent_id
        })
        return {"error": error_msg}
    if schedule_options > 1:
        error_msg = "Cannot specify multiple scheduling options"
        logger.error(error_msg, extra={
            'operation_type': 'register_prompt',
            'error_type': 'multiple_schedule_options',
            'agent_id': agent_id,
            'time_provided': bool(time_str),
            'cron_provided': bool(cron_expr),
            'every_provided': bool(every_str)
        })
        return {"error": error_msg}
    
    # Validate agent exists unless skipped
    if not skip_validation:
        logger.debug("Validating agent existence", extra={
            'operation_type': 'register_prompt',
            'agent_id': agent_id,
            'validation_step': 'agent_exists'
        })
        validation_result = validate_agent_exists(agent_id)
        if validation_result["status"] == "error":
            error_msg = f"Agent validation failed: {validation_result['message']}"
            logger.error(error_msg, extra={
                'operation_type': 'register_prompt',
                'error_type': 'agent_validation_failed',
                'agent_id': agent_id,
                'validation_message': validation_result['message']
            })
            return {"error": error_msg}
    
    def _normalize_iso(value: str) -> str:
        """Normalize common datetime strings to ISO 8601.
        - Preserve exact ISO (including trailing 'Z').
        - Convert 'YYYY-MM-DD HH:MM:SS UTC' to 'YYYY-MM-DDTHH:MM:SSZ'.
        - Trim whitespace.
        """
        v = value.strip()
        if v.endswith('Z'):
            return v
        if v.upper().endswith(' UTC'):
            core = v[:-4].strip()
            if 'T' not in core and ' ' in core:
                date_part, time_part = core.split(' ', 1)
                core = f"{date_part}T{time_part}"
            return f"{core}Z"
        return v

    try:
        if time_str:
            # One-time schedule
            try:
                # Prefer strict ISO parsing; fall back to flexible parse
                norm = _normalize_iso(time_str)
                next_run = date_parser.isoparse(norm)
            except Exception:
                next_run = date_parser.parse(time_str)
            # Compare using a matching reference clock: local for naive, same tz for aware
            now_ref = datetime.now(tz=next_run.tzinfo) if next_run.tzinfo else datetime.now()
            if next_run <= now_ref:
                return {"error": "Scheduled time must be in the future"}
            
            schedule_type = "once"
            schedule_value = time_str
            
        elif cron_expr:
            # Recurring schedule
            if not croniter.is_valid(cron_expr):
                return {"error": f"Invalid cron expression: {cron_expr}"}
            
            schedule_type = "cron"
            schedule_value = cron_expr
            next_run = calculate_next_run(cron_expr)
            
        elif every_str:
            # Interval schedule
            schedule_type = "interval"
            schedule_value = every_str
            
            # Parse interval and calculate next run
            try:
                if every_str.endswith('s'):
                    seconds = int(every_str[:-1])
                elif every_str.endswith('m'):
                    seconds = int(every_str[:-1]) * 60
                elif every_str.endswith('h'):
                    seconds = int(every_str[:-1]) * 3600
                else:
                    seconds = int(every_str)  # Default to seconds
                
                # Handle start_at parameter for interval schedules
                if start_at:
                    try:
                        norm_start = _normalize_iso(start_at)
                        next_run = date_parser.isoparse(norm_start)
                    except Exception:
                        next_run = date_parser.parse(start_at)
                    # Use matching reference clock for validity check
                    start_ref = datetime.now(tz=next_run.tzinfo) if next_run.tzinfo else datetime.now()
                    if next_run <= start_ref:
                        return {"error": "Start time must be in the future"}
                else:
                    next_run = datetime.utcnow() + timedelta(seconds=seconds)
            except ValueError:
                return {"error": f"Invalid interval format: {every_str}. Use formats like '30s', '5m', '1h'"}
        
        # Validate parsed time_str explicitly to improve error clarity
        if time_str:
            try:
                _ = next_run  # ensure set
            except NameError:
                return {"error": "Invalid time format. Use ISO 8601 like 2025-12-25T10:00:00Z or include offset, e.g. 2025-12-25T10:00:00-05:00"}
        
        # Validate max_repetitions if provided
        if max_repetitions is not None:
            try:
                max_repetitions = int(max_repetitions)
                if max_repetitions <= 0:
                    return {"error": "max-repetitions must be a positive integer"}
            except ValueError:
                return {"error": "max-repetitions must be a valid integer"}
        
        schedule_id = add_schedule(
            agent_id=agent_id,
            prompt_text=prompt,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            next_run=next_run,
            max_repetitions=max_repetitions
        )
        
        register_time = time.time() - start_time
        
        logger.info("Prompt registration successful", extra={
            'operation_type': 'register_prompt',
            'agent_id': agent_id,
            'schedule_id': schedule_id,
            'schedule_type': schedule_type,
            'schedule_value': schedule_value,
            'next_run': next_run.isoformat(),
            'max_repetitions': max_repetitions,
            'register_time_ms': round(register_time * 1000, 2)
        })
        
        return {
            "status": "success",
            "id": schedule_id,
            "next_run": next_run.isoformat(),
            "message": f"Prompt scheduled with ID {schedule_id}"
        }
        
    except Exception as e:
        register_time = time.time() - start_time
        error_msg = f"Failed to register prompt: {str(e)}"
        logger.error(error_msg, extra={
            'operation_type': 'register_prompt',
            'agent_id': agent_id,
            'error': str(e),
            'error_type': type(e).__name__,
            'register_time_ms': round(register_time * 1000, 2)
        })
        return {"error": error_msg}


def list_prompts(args: Dict[str, Any]) -> Dict[str, Any]:
    """List scheduled prompts."""
    start_time = time.time()
    
    agent_id = args.get("agent_id") or args.get("agent-id")
    show_all = args.get("all", False)
    
    logger.info("Starting prompt listing", extra={
        'operation_type': 'list_prompts',
        'agent_id': agent_id,
        'show_all': show_all
    })
    
    try:
        logger.debug(f"Calling list_schedules with agent_id={agent_id}, active_only={not show_all}", extra={
            'operation_type': 'list_prompts',
            'agent_id': agent_id,
            'active_only': not show_all
        })
        
        schedules = list_schedules(
            agent_id=agent_id,
            active_only=not show_all
        )
        
        list_time = time.time() - start_time
        
        logger.info("Prompt listing successful", extra={
            'operation_type': 'list_prompts',
            'agent_id': agent_id,
            'schedules_count': len(schedules),
            'show_all': show_all,
            'list_time_ms': round(list_time * 1000, 2)
        })
        
        return {
            "status": "success",
            "schedules": schedules,
            "count": len(schedules)
        }
        
    except Exception as e:
        list_time = time.time() - start_time
        error_msg = f"Failed to list prompts: {str(e)}"
        logger.error(error_msg, extra={
            'operation_type': 'list_prompts',
            'agent_id': agent_id,
            'error': str(e),
            'error_type': type(e).__name__,
            'list_time_ms': round(list_time * 1000, 2)
        })
        return {"error": error_msg}


def cancel_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    """Cancel a scheduled prompt."""
    start_time = time.time()
    
    schedule_id = args.get("id")
    
    logger.info("Starting prompt cancellation", extra={
        'operation_type': 'cancel_prompt',
        'schedule_id_raw': schedule_id
    })
    
    if not schedule_id:
        error_msg = "Missing required argument: id"
        logger.error(error_msg, extra={
            'operation_type': 'cancel_prompt',
            'error_type': 'missing_id'
        })
        return {"error": error_msg}
    
    try:
        schedule_id = int(schedule_id)
        logger.debug("Calling cancel_schedule", extra={
            'operation_type': 'cancel_prompt',
            'schedule_id': schedule_id
        })
        
        success = cancel_schedule(schedule_id)
        cancel_time = time.time() - start_time
        
        if success:
            logger.info("Prompt cancellation successful", extra={
                'operation_type': 'cancel_prompt',
                'schedule_id': schedule_id,
                'cancel_time_ms': round(cancel_time * 1000, 2)
            })
            return {
                "status": "success",
                "cancelled_id": schedule_id,
                "message": f"Schedule {schedule_id} cancelled"
            }
        else:
            error_msg = f"Schedule {schedule_id} not found or already cancelled"
            logger.error(error_msg, extra={
                'operation_type': 'cancel_prompt',
                'schedule_id': schedule_id,
                'error_type': 'not_found_or_cancelled',
                'cancel_time_ms': round(cancel_time * 1000, 2)
            })
            return {"error": error_msg}
            
    except ValueError:
        cancel_time = time.time() - start_time
        error_msg = "Schedule ID must be a number"
        logger.error(error_msg, extra={
            'operation_type': 'cancel_prompt',
            'schedule_id_raw': schedule_id,
            'error_type': 'invalid_id_format',
            'cancel_time_ms': round(cancel_time * 1000, 2)
        })
        return {"error": error_msg}
    except Exception as e:
        cancel_time = time.time() - start_time
        error_msg = f"Failed to cancel prompt: {str(e)}"
        logger.error(error_msg, extra={
            'operation_type': 'cancel_prompt',
            'schedule_id': schedule_id,
            'error': str(e),
            'error_type': type(e).__name__,
            'cancel_time_ms': round(cancel_time * 1000, 2)
        })
        return {"error": error_msg}


def test_connection(args: Dict[str, Any]) -> Dict[str, Any]:
    """Test connection to Letta server."""
    start_time = time.time()
    
    logger.info("Starting connection test", extra={
        'operation_type': 'test_connection'
    })
    
    try:
        result = test_letta_connection()
        test_time = time.time() - start_time
        
        logger.info("Connection test completed", extra={
            'operation_type': 'test_connection',
            'status': result.get('status'),
            'test_time_ms': round(test_time * 1000, 2)
        })
        
        return result
    except Exception as e:
        test_time = time.time() - start_time
        error_msg = f"Failed to test connection: {str(e)}"
        logger.error(error_msg, extra={
            'operation_type': 'test_connection',
            'error': str(e),
            'error_type': type(e).__name__,
            'test_time_ms': round(test_time * 1000, 2)
        })
        return {"error": error_msg}


def list_agents(args: Dict[str, Any]) -> Dict[str, Any]:
    """List available agents from Letta server."""
    start_time = time.time()
    
    logger.info("Starting agent listing", extra={
        'operation_type': 'list_agents'
    })
    
    try:
        result = list_available_agents()
        list_time = time.time() - start_time
        
        logger.info("Agent listing completed", extra={
            'operation_type': 'list_agents',
            'status': result.get('status'),
            'agents_count': len(result.get('agents', [])) if 'agents' in result else 0,
            'list_time_ms': round(list_time * 1000, 2)
        })
        
        return result
    except Exception as e:
        list_time = time.time() - start_time
        error_msg = f"Failed to list agents: {str(e)}"
        logger.error(error_msg, extra={
            'operation_type': 'list_agents',
            'error': str(e),
            'error_type': type(e).__name__,
            'list_time_ms': round(list_time * 1000, 2)
        })
        return {"error": error_msg}


def execute_prompts(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute due prompts."""
    start_time = time.time()
    
    loop_mode = args.get("loop", False)
    interval = args.get("interval", 60)
    
    logger.info("Starting prompt execution", extra={
        'operation_type': 'execute_prompts',
        'loop_mode': loop_mode,
        'interval': interval
    })
    
    try:
        if loop_mode:
            # Run in loop mode using scheduler
            try:
                interval_seconds = int(interval)
            except ValueError:
                error_msg = "Interval must be a number (seconds)"
                logger.error(error_msg, extra={
                    'operation_type': 'execute_prompts',
                    'error_type': 'invalid_interval',
                    'interval_value': interval
                })
                return {"error": error_msg}
            
            logger.info("Starting scheduler loop", extra={
                'operation_type': 'execute_prompts',
                'mode': 'loop',
                'interval_seconds': interval_seconds
            })
            
            run_scheduler_loop(interval_seconds)
            exec_time = time.time() - start_time
            
            logger.info("Scheduler loop completed", extra={
                'operation_type': 'execute_prompts',
                'mode': 'loop',
                'exec_time_ms': round(exec_time * 1000, 2)
            })
            
            return {
                "status": "success",
                "message": "Scheduler loop completed"
            }
        else:
            logger.debug("Executing due prompts once", extra={
                'operation_type': 'execute_prompts',
                'mode': 'once'
            })
            
            results = execute_due_prompts()
            exec_time = time.time() - start_time
            
            logger.info("Prompt execution completed", extra={
                'operation_type': 'execute_prompts',
                'mode': 'once',
                'prompts_executed': len(results),
                'exec_time_ms': round(exec_time * 1000, 2)
            })
            
            return {
                "status": "success",
                "executed": results,
                "message": f"{len(results)} prompts executed"
            }
            
    except Exception as e:
        exec_time = time.time() - start_time
        error_msg = f"Failed to execute prompts: {str(e)}"
        logger.error(error_msg, extra={
            'operation_type': 'execute_prompts',
            'loop_mode': loop_mode,
            'error': str(e),
            'error_type': type(e).__name__,
            'exec_time_ms': round(exec_time * 1000, 2)
        })
        return {"error": error_msg}


def main():
    start_time = time.time()
    
    logger.info("CLI main() started", extra={
        'operation_type': 'cli_main'
    })
    
    parser = argparse.ArgumentParser(
        description="Promptyoself CLI – Schedule and manage prompts for Letta agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  register    Register a new scheduled prompt
  list        List scheduled prompts
  cancel      Cancel a scheduled prompt
  execute     Execute due prompts
  test        Test connection to Letta server
  agents      List available agents

Examples:
  python cli.py register --agent-id agent-123 --prompt "Check status" --time "2024-01-01 14:30:00"
  python cli.py register --agent-id agent-123 --prompt "Daily report" --cron "0 9 * * *"
  python cli.py register --agent-id agent-123 --prompt "Every 5 minutes" --every "5m"
  python cli.py register --agent-id agent-123 --prompt "Focus check" --every "6m" --max-repetitions 10 --start-at "2024-01-01 15:00:00"
  python cli.py list --agent-id agent-123
  python cli.py cancel --id 5
  python cli.py execute
  python cli.py execute --loop --interval 30
  python cli.py test
  python cli.py agents
        """
    )
    
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register a new scheduled prompt")
    register_parser.add_argument("--agent-id", required=True, help="Target agent ID")
    register_parser.add_argument("--prompt", required=True, help="Prompt content to schedule")
    register_parser.add_argument("--time", help="One-time execution time (ISO format)")
    register_parser.add_argument("--cron", help="Cron expression for recurring execution")
    register_parser.add_argument("--every", help="Interval for recurring execution (e.g., '5m', '1h', '30s')")
    register_parser.add_argument("--max-repetitions", type=int, help="Maximum number of repetitions (for --every schedules)")
    register_parser.add_argument("--start-at", help="Start time for interval schedules (ISO format)")
    register_parser.add_argument("--skip-validation", action="store_true", help="Skip agent validation")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List scheduled prompts")
    list_parser.add_argument("--agent-id", help="Filter by agent ID")
    list_parser.add_argument("--all", action="store_true", help="Include cancelled schedules")
    
    # Cancel command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a scheduled prompt")
    cancel_parser.add_argument("--id", required=True, help="Schedule ID to cancel")
    
    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Execute due prompts")
    execute_parser.add_argument("--loop", action="store_true", help="Run continuously")
    execute_parser.add_argument("--interval", type=int, default=60, help="Interval in seconds for loop mode (default: 60)")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test connection to Letta server")
    
    # Agents command
    agents_parser = subparsers.add_parser("agents", help="List available agents")

    # Upload tool command (meta-tool)
    upload_parser = subparsers.add_parser("upload", help="Upload a Letta-native tool from source code")
    upload_parser.add_argument("--name", required=False, help="Optional name for logs")
    upload_parser.add_argument("--description", required=False, help="Description for the tool in Letta")
    upload_parser.add_argument("--source-code", required=True, help="Complete Python function source code string")
    
    args = parser.parse_args()
    
    # Convert args to dict for easier handling
    args_dict = vars(args)
    command = args_dict.pop("command")
    
    logger.info("CLI command dispatching", extra={
        'operation_type': 'cli_main',
        'command': command,
        'command_args': {k: v for k, v in args_dict.items() if k not in ['prompt']}  # Exclude prompt text for privacy
    })
    
    # Dispatch to appropriate function
    if command == "register":
        result = register_prompt(args_dict)
    elif command == "list":
        result = list_prompts(args_dict)
    elif command == "cancel":
        result = cancel_prompt(args_dict)
    elif command == "execute":
        result = execute_prompts(args_dict)
    elif command == "test":
        result = test_connection(args_dict)
    elif command == "agents":
        result = list_agents(args_dict)
    elif command == "upload":
        result = upload_tool({
            "name": args_dict.get("name"),
            "description": args_dict.get("description"),
            "source_code": args_dict.get("source_code") or args_dict.get("source-code"),
        })
    else:
        result = {"error": f"Unknown command: {command}"}
    
    # Output JSON result
    main_time = time.time() - start_time
    success = result.get("status") == "success" or "error" not in result
    
    logger.info("CLI command completed", extra={
        'operation_type': 'cli_main',
        'command': command,
        'status': 'success' if success else 'error',
        'has_error': 'error' in result,
        'main_time_ms': round(main_time * 1000, 2)
    })
    
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)



def promptyoself_schedule(agent_id: str, prompt: str, time: str = None,
                          cron: str = None, every: str = None,
                          skip_validation: bool = False, max_repetitions: int = None,
                          start_at: str = None) -> str:
    """Register a new scheduled prompt for yourself. Exactly one of time, cron, or every must be provided. Make sure to include you own own agent ID."""
    args = {
        "agent_id": agent_id,
        "prompt": prompt,
        "time": time,
        "cron": cron,
        "every": every,
        "skip_validation": skip_validation,
        "max_repetitions": max_repetitions,
        "start_at": start_at,
    }
    result = register_prompt(args)
    return json.dumps(result, indent=2)


def promptyoself_list(agent_id: str = None, active_only: bool = True, 
                     limit: int = None) -> str:
    """
    List scheduled prompts, optionally filtered by agent.

    Args:
        agent_id (str, optional): Filter schedules for a specific agent ID. Defaults to None.
        active_only (bool, optional): Show only active schedules. Defaults to True.
        limit (int, optional): Maximum number of schedules to return. Defaults to None.

    Returns:
        str: JSON response containing the list of schedules.
    """
    args = {
        "agent_id": agent_id,
        "active_only": active_only,
        "limit": limit
    }
    result = list_prompts(args)
    return json.dumps(result, indent=2)


def promptyoself_cancel(schedule_id: str) -> str:
    """
    Cancel a scheduled prompt by its ID.

    Args:
        schedule_id (str): The unique ID of the schedule to cancel.

    Returns:
        str: JSON response confirming the cancellation status.
    """
    args = {"schedule_id": schedule_id}
    result = cancel_prompt(args)
    return json.dumps(result, indent=2)


def promptyoself_execute(daemon: bool = False, once: bool = False) -> str:
    """
    Execute due scheduled prompts immediately or start daemon mode.

    Args:
        daemon (bool, optional): Run in background daemon mode for continuous execution. Defaults to False.
        once (bool, optional): Execute due prompts once and exit. Defaults to False.

    Returns:
        str: JSON response with execution results and statistics.
    """
    args = {
        "daemon": daemon,
        "once": once
    }
    result = execute_prompts(args)
    return json.dumps(result, indent=2)


def promptyoself_test() -> str:
    """
    Test the connection to the Letta server and verify functionality.

    Returns:
        str: JSON response with connection status and server information.
    """
    args = {}
    result = test_connection(args)
    return json.dumps(result, indent=2)


def promptyoself_agents() -> str:
    """
    List all available Letta agents that can receive scheduled prompts.

    Returns:
        str: JSON response containing the list of available agents.
    """
    args = {}
    result = list_agents(args)
    return json.dumps(result, indent=2)


def upload_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upload a Python function as a native Letta tool via the Letta API.

    Args:
        name (str, optional): Optional name for logs; Letta derives tool name from the function.
        description (str, optional): Tool description stored in Letta.
        source_code (str): Complete top-level function with docstring and type hints.

    Returns:
        Dict[str, Any]: Result from the Letta API or error details.
    """
    try:
        from letta_client import Letta
        import os
        token = os.getenv("LETTA_API_KEY") or os.getenv("LETTA_SERVER_PASSWORD")
        base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")  # Default to local server
        if not token:
            return {"error": "Missing LETTA_API_KEY or LETTA_SERVER_PASSWORD"}
        client = Letta(token=token, base_url=base_url)
        resp = client.tools.upsert(
            source_code=args.get("source_code"),
            description=args.get("description")
        )
        return {"status": "success", "tool_id": resp.id, "name": getattr(resp, 'name', None)}
    except Exception as e:
        return {"error": f"Upload failed: {e}"}


def promptyoself_upload(name: str | None, description: str | None, source_code: str) -> str:
    """
    Upload a Letta-native tool from complete Python source code.

    Args:
        name (str, optional): Optional reference name for logs. The actual tool name derives from the function.
        description (str, optional): Tool description stored in Letta.
        source_code (str): A complete, top-level Python function definition with a detailed docstring and type hints.

    Returns:
        str: JSON string indicating success or error returned by the Letta API.
    """
    args = {
        "name": name,
        "description": description,
        "source_code": source_code,
    }
    result = upload_tool(args)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    main()
