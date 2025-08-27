"""
Letta client integration for promptyoself plugin.
Provides helper functions that wrap the official letta-client SDK.
"""

import os
import time
from typing import Dict, Any, List, Optional, Union

from letta_client import Letta, MessageCreate, TextContent

# Import our structured logging
try:
    from .logging_config import get_logger, PerformanceTimer
except ImportError:
    # Fallback for when running as script
    from logging_config import get_logger, PerformanceTimer

logger = get_logger(__name__)

_letta_client: Optional[Letta] = None


def _get_letta_client() -> Letta:
    """Return a singleton instance of the Letta SDK client."""
    global _letta_client

    if _letta_client is None:
        logger.info("Initializing Letta client", extra={
            'operation_type': 'letta_api',
            'letta_operation': 'client_init'
        })
        
        token = os.getenv("LETTA_API_KEY")
        base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")  # Default to local server
        password = os.getenv("LETTA_SERVER_PASSWORD")

        auth_method = "api_key"
        if not token:
            if password:
                # Use password for Bearer token authentication
                token = password
                auth_method = "server_password"
                logger.debug("Using LETTA_SERVER_PASSWORD for Bearer token authentication", extra={
                    'operation_type': 'letta_api',
                    'auth_method': auth_method
                })
            else:
                # Try with a dummy token for unsecured servers
                token = "dummy-token-for-unsecured-server"
                auth_method = "dummy_token"
                logger.debug("No LETTA_API_KEY or LETTA_SERVER_PASSWORD provided, using dummy token for unsecured server", extra={
                    'operation_type': 'letta_api',
                    'auth_method': auth_method
                })

        try:
            logger.debug("Creating Letta client instance", extra={
                'operation_type': 'letta_api',
                'letta_operation': 'client_create',
                'base_url': base_url or "cloud_default",
                'auth_method': auth_method
            })
            
            _letta_client = Letta(token=token, base_url=base_url)
            
            logger.info("Letta client initialized successfully", extra={
                'operation_type': 'letta_api',
                'letta_operation': 'client_init',
                'base_url': base_url or "cloud_default",
                'auth_method': auth_method
            })
        except Exception as e:
            logger.error("Failed to initialize Letta client", extra={
                'operation_type': 'letta_api',
                'letta_operation': 'client_init',
                'base_url': base_url or "cloud_default",
                'auth_method': auth_method,
                'error': str(e)
            }, exc_info=True)
            raise

    return _letta_client


def send_prompt_to_agent(agent_id: str, prompt_text: str, max_retries: int = 3) -> bool:
    """
    Send a prompt message to a Letta agent with enhanced error handling.

    Args:
        agent_id: The Letta agent ID.
        prompt_text: Text content of the prompt.
        max_retries: Maximum number of retry attempts.

    Returns:
        Boolean indicating success or failure.
    """
    for attempt in range(max_retries):
        try:
            client = _get_letta_client()
            
            logger.info("Sending prompt to agent", extra={
                'operation_type': 'letta_api',
                'letta_operation': 'send_prompt',
                'agent_id': agent_id,
                'attempt': attempt + 1,
                'max_retries': max_retries,
                'prompt_length': len(prompt_text)
            })
            
            # Try standard message delivery
            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[
                    MessageCreate(
                        role="user",
                        content=[
                            TextContent(
                                text=prompt_text,
                            )
                        ],
                    )
                ],
            )
            logger.info("Successfully sent prompt to agent", extra={
                'operation_type': 'letta_api',
                'letta_operation': 'send_prompt',
                'agent_id': agent_id,
                'attempt': attempt + 1,
                'success': True,
                'prompt_length': len(prompt_text)
            })
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.warning("Prompt delivery attempt failed", extra={
                'operation_type': 'letta_api',
                'letta_operation': 'send_prompt',
                'agent_id': agent_id,
                'attempt': attempt + 1,
                'max_retries': max_retries,
                'success': False,
                'error': error_msg,
                'prompt_length': len(prompt_text)
            })
            
            # Check if it's the ChatML description bug
            if "'description'" in error_msg and "ChatMLInnerMonologueWrapper" in error_msg:
                logger.info("Detected ChatML description bug, attempting streaming fallback")
                if _try_streaming_fallback(agent_id, prompt_text):
                    return True
            
            # If this is the last attempt, don't retry
            if attempt == max_retries - 1:
                logger.error("All %d attempts failed for agent %s: %s", max_retries, agent_id, error_msg)
                return False
            
            # Exponential backoff: wait 1s, then 2s, then 4s
            wait_time = 2 ** attempt
            logger.info("Retrying in %d seconds...", wait_time)
            time.sleep(wait_time)
    
    return False


def _try_streaming_fallback(agent_id: str, prompt_text: str) -> bool:
    """
    Attempt to send prompt using streaming API as fallback.
    
    Args:
        agent_id: The Letta agent ID.
        prompt_text: Text content of the prompt.
        
    Returns:
        Boolean indicating success or failure.
    """
    try:
        client = _get_letta_client()
        
        logger.info("Attempting streaming fallback for agent %s", agent_id)
        
        # Try using streaming API
        response = client.agents.messages.create_stream(
            agent_id=agent_id,
            messages=[
                MessageCreate(
                    role="user",
                    content=[
                        TextContent(
                            text=prompt_text,
                        )
                    ],
                )
            ],
        )
        
        # Process streaming response
        for chunk in response:
            # Just consume the stream - we don't need to process the response
            pass
        
        logger.info("Streaming fallback successful for agent %s", agent_id)
        return True
        
    except Exception as e:
        logger.error("Streaming fallback failed for agent %s: %s", agent_id, str(e))
        return False


def send_prompt_to_agent_streaming_only(agent_id: str, prompt_text: str, max_retries: int = 3) -> bool:
    """
    Send a prompt message using ONLY the streaming API (no standard API fallback).
    
    Args:
        agent_id: The Letta agent ID.
        prompt_text: Text content of the prompt.
        max_retries: Maximum number of retry attempts.
        
    Returns:
        Boolean indicating success or failure.
    """
    for attempt in range(max_retries):
        try:
            client = _get_letta_client()
            
            logger.info("Streaming-only attempt %d/%d for agent %s", attempt + 1, max_retries, agent_id)
            
            # Use ONLY streaming API
            response = client.agents.messages.create_stream(
                agent_id=agent_id,
                messages=[
                    MessageCreate(
                        role="user",
                        content=[
                            TextContent(
                                text=prompt_text,
                            )
                        ],
                    )
                ],
            )
            
            # Process streaming response
            for chunk in response:
                # Just consume the stream - we don't need to process the response
                pass
            
            logger.info("Streaming-only delivery successful for agent %s", agent_id)
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.warning("Streaming-only attempt %d/%d failed for agent %s: %s", attempt + 1, max_retries, agent_id, error_msg)
            
            # If this is the last attempt, don't retry
            if attempt == max_retries - 1:
                logger.error("All %d streaming-only attempts failed for agent %s: %s", max_retries, agent_id, error_msg)
                return False
            
            # Exponential backoff: wait 1s, then 2s, then 4s
            wait_time = 2 ** attempt
            logger.info("Retrying streaming-only in %d seconds...", wait_time)
            time.sleep(wait_time)
    
    return False


def send_prompt_to_agent_with_detailed_logging(agent_id: str, prompt_text: str) -> Dict[str, Any]:
    """
    Send prompt with detailed logging for debugging.
    
    Args:
        agent_id: The Letta agent ID.
        prompt_text: Text content of the prompt.
        
    Returns:
        Dict with detailed results.
    """
    result: Dict[str, Any] = {
        "agent_id": agent_id,
        "prompt_text": prompt_text,
        "success": False,
        "error": None,
        "attempts": []
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        attempt_result = {
            "attempt": attempt + 1,
            "timestamp": time.time(),
            "success": False,
            "error": None,
            "method": "standard"
        }
        
        try:
            client = _get_letta_client()
            
            logger.info("Detailed attempt %d/%d for agent %s", attempt + 1, max_retries, agent_id)
            
            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[
                    MessageCreate(
                        role="user",
                        content=[
                            TextContent(
                                text=prompt_text,
                            )
                        ],
                    )
                ],
            )
            
            attempt_result["success"] = True
            result["success"] = True
            result["attempts"].append(attempt_result)
            logger.info("Detailed attempt %d successful for agent %s", attempt + 1, agent_id)
            return result
            
        except Exception as e:
            error_msg = str(e)
            attempt_result["error"] = error_msg
            result["attempts"].append(attempt_result)
            
            logger.warning("Detailed attempt %d failed for agent %s: %s", attempt + 1, agent_id, error_msg)
            
            # Try streaming fallback on ChatML bug
            if "'description'" in error_msg and "ChatMLInnerMonologueWrapper" in error_msg:
                stream_attempt = {
                    "attempt": attempt + 1,
                    "timestamp": time.time(),
                    "success": False,
                    "error": None,
                    "method": "streaming"
                }
                
                try:
                    logger.info("Attempting streaming fallback for agent %s", agent_id)
                    
                    stream_response = client.agents.messages.create_stream(
                        agent_id=agent_id,
                        messages=[
                            MessageCreate(
                                role="user",
                                content=[
                                    TextContent(
                                        text=prompt_text,
                                    )
                                ],
                            )
                        ],
                    )
                    
                    # Process streaming response
                    for chunk in stream_response:
                        pass
                    
                    stream_attempt["success"] = True
                    result["success"] = True
                    result["attempts"].append(stream_attempt)
                    logger.info("Streaming fallback successful for agent %s", agent_id)
                    return result
                    
                except Exception as stream_e:
                    stream_attempt["error"] = str(stream_e)
                    result["attempts"].append(stream_attempt)
                    logger.error("Streaming fallback failed for agent %s: %s", agent_id, str(stream_e))
            
            # If this is the last attempt, don't retry
            if attempt == max_retries - 1:
                result["error"] = f"All {max_retries} attempts failed. Last error: {error_msg}"
                logger.error("All detailed attempts failed for agent %s", agent_id)
                return result
            
            # Exponential backoff
            wait_time = 2 ** attempt
            logger.info("Waiting %d seconds before retry...", wait_time)
            time.sleep(wait_time)
    
    return result


def test_letta_connection() -> Dict[str, Any]:
    """
    Test connection to Letta server.
    
    Returns:
        Status dict with connection test results.
    """
    try:
        client = _get_letta_client()
        # Try to list agents as a simple connectivity test
        agents = client.agents.list()
        return {
            "status": "success",
            "message": "Connection to Letta server successful",
            "agent_count": len(agents)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to Letta server: {str(e)}"
        }


def list_available_agents() -> Dict[str, Any]:
    """
    List all available agents from Letta server.
    
    Returns:
        Dict with agent list or error message.
    """
    try:
        client = _get_letta_client()
        agents = client.agents.list()
        
        agent_list = []
        for agent in agents:
            created_at = getattr(agent, 'created_at', None)
            last_updated = getattr(agent, 'last_updated', None)
            
            agent_list.append({
                "id": agent.id,
                "name": getattr(agent, 'name', 'Unknown'),
                "created_at": created_at.isoformat() if created_at else None,
                "last_updated": last_updated.isoformat() if last_updated else None
            })
        
        return {
            "status": "success",
            "agents": agent_list,
            "count": len(agent_list)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list agents: {str(e)}"
        }


def validate_agent_exists(agent_id: str) -> Dict[str, Any]:
    """
    Validate that an agent exists on the Letta server.
    
    Args:
        agent_id: The agent ID to validate.
        
    Returns:
        Dict with validation results.
    """
    try:
        client = _get_letta_client()
        agents = client.agents.list()
        
        # Look for the agent in the list
        for agent in agents:
            if agent.id == agent_id:
                return {
                    "status": "success",
                    "exists": True,
                    "agent_id": agent_id,
                    "agent_name": getattr(agent, 'name', 'Unknown')
                }
        
        # Agent not found
        return {
            "status": "error",
            "exists": False,
            "message": f"Agent {agent_id} not found"
        }
    except Exception as e:
        return {
            "status": "error",
            "exists": False,
            "message": f"Failed to validate agent {agent_id}: {str(e)}"
        }


if __name__ == "__main__":
    # Manual smoke test
    import json
    import sys

    test_agent_id = os.getenv("TEST_AGENT_ID")
    if not test_agent_id:
        sys.exit("Set TEST_AGENT_ID env var to run this test")

    # Test connection
    print("Testing connection...")
    conn_result = test_letta_connection()
    print(json.dumps(conn_result, indent=2))
    
    # Test sending prompt
    print("\nTesting prompt sending...")
    success = send_prompt_to_agent(test_agent_id, "Hello from promptyoself!")
    print(f"Prompt sent successfully: {success}")
    
    # Test detailed logging
    print("\nTesting detailed logging...")
    detailed_result = send_prompt_to_agent_with_detailed_logging(test_agent_id, "Hello with detailed logging!")
    print(json.dumps(detailed_result, indent=2))
    
    # Test listing agents
    print("\nTesting agent listing...")
    agents_result = list_available_agents()
    print(json.dumps(agents_result, indent=2))