# Test Plan: Promptyoself Test Coverage Improvement

## Summary

**Current Coverage:** 26.27%  
**Target Coverage:** >80%  
**Strategy:** Prioritize files with lowest coverage and highest impact, focusing on API error handling, CLI command variations, database edge cases, and scheduler functionality.

## Testing Priorities

1. **`promptyoself/letta_api.py`** (10% coverage) - Highest priority due to critical API integration
2. **`promptyoself/cli.py`** (13% coverage) - Core user interface functionality
3. **`promptyoself/scheduler.py`** (17% coverage) - Background scheduling operations
4. **`promptyoself/db.py`** (35% coverage) - Database operations and data persistence
5. **`promptyoself_mcp_server.py`** (42% coverage) - MCP server integration

## Detailed Test Cases by File

### promptyoself/letta_api.py

#### Function: `_get_letta_client()`
- Test client initialization with valid LETTA_API_KEY environment variable
- Test client initialization with LETTA_SERVER_PASSWORD environment variable
- Test client initialization with no authentication (dummy token fallback)
- Test client initialization failure scenarios (invalid URLs, network errors)
- Test singleton behavior (multiple calls return same instance)

#### Function: `send_prompt_to_agent()`
- Test successful prompt delivery with valid agent ID and prompt text
- Test retry mechanism with temporary failures (3 attempts with exponential backoff)
- Test ChatML description bug detection and streaming fallback
- Test failure after maximum retries exceeded
- Test error handling for invalid agent IDs
- Test error handling for network timeouts
- Test error handling for authentication failures

#### Function: `_try_streaming_fallback()`
- Test successful streaming fallback operation
- Test streaming fallback failure scenarios
- Test error handling for streaming API failures

#### Function: `send_prompt_to_agent_streaming_only()`
- Test streaming-only delivery success
- Test streaming-only retry mechanism
- Test streaming-only failure scenarios

#### Function: `send_prompt_to_agent_with_detailed_logging()`
- Test detailed logging for successful deliveries
- Test detailed logging for failed attempts
- Test streaming fallback within detailed logging context
- Test error accumulation in detailed results

#### Function: `test_letta_connection()`
- Test successful connection to Letta server
- Test connection failure scenarios (server down, network issues)
- Test agent listing as connectivity verification

#### Function: `list_available_agents()`
- Test successful agent listing
- Test agent listing failure scenarios
- Test agent metadata extraction (name, timestamps)

#### Function: `validate_agent_exists()`
- Test validation for existing agents
- Test validation for non-existent agents
- Test validation failure scenarios (server errors)

### promptyoself/cli.py

#### Function: `register_prompt()`
- Test registration with time-based scheduling (ISO format)
- Test registration with cron expressions
- Test registration with interval scheduling (seconds, minutes, hours)
- Test validation of required arguments (agent_id, prompt)
- Test validation of scheduling options (exactly one required)
- Test agent validation skip option
- Test max_repetitions validation (positive integers)
- Test start_at parameter validation for interval schedules
- Test error handling for invalid cron expressions
- Test error handling for invalid time formats
- Test error handling for invalid interval formats

#### Function: `list_prompts()`
- Test listing all prompts (active only)
- Test listing with agent_id filter
- Test listing including cancelled schedules
- Test error handling for database query failures

#### Function: `cancel_prompt()`
- Test successful schedule cancellation
- Test cancellation of non-existent schedules
- Test cancellation of already cancelled schedules
- Test error handling for invalid schedule ID formats
- Test error handling for database operation failures

#### Function: `test_connection()`
- Test connection test functionality
- Test error propagation from underlying API

#### Function: `list_agents()`
- Test agent listing functionality
- Test error handling for agent listing failures

#### Function: `execute_prompts()`
- Test single execution mode (execute due prompts once)
- Test loop execution mode with various intervals
- Test error handling for invalid interval values
- Test error handling for execution failures

#### Function: `upload_tool()`
- Test tool upload with valid source code
- Test tool upload with description
- Test tool upload failure (missing authentication)
- Test error handling for upload failures

#### MCP Tool Wrapper Functions
- Test `promptyoself_register()` parameter validation and error handling
- Test `promptyoself_list()` filtering and formatting
- Test `promptyoself_cancel()` ID validation
- Test `promptyoself_execute()` mode switching
- Test `promptyoself_test()` connectivity testing
- Test `promptyoself_agents()` agent listing
- Test `promptyoself_upload()` source code validation

### promptyoself/scheduler.py

#### Function: `calculate_next_run()`
- Test cron expression parsing and next run calculation
- Test base time parameter functionality
- Test error handling for invalid cron expressions

#### Function: `calculate_next_run_for_schedule()`
- Test next run calculation for cron schedules
- Test next run calculation for interval schedules
- Test next run calculation for one-time schedules
- Test error handling for unknown schedule types

#### Function: `execute_due_prompts()`
- Test execution with no due schedules
- Test execution with multiple due schedules
- Test successful prompt delivery and schedule updating
- Test failed prompt delivery and retry scheduling
- Test repetition counting and max_repetitions enforcement
- Test one-time schedule deactivation after execution
- Test error handling for individual schedule failures
- Test error handling for critical execution failures

#### Class: `PromptScheduler`
- Test scheduler start/stop functionality
- Test job execution interval adherence
- Test error handling in background jobs
- Test graceful shutdown on interrupt

#### Function: `run_scheduler_loop()`
- Test loop initialization and execution
- Test interrupt handling
- Test resource cleanup

### promptyoself/db.py

#### Database Initialization
- Test database engine creation with different file paths
- Test table creation and schema validation
- Test session factory initialization
- Test error handling for database file creation issues

#### Function: `initialize_db()`
- Test database initialization success
- Test error handling for table creation failures

#### Function: `add_schedule()`
- Test schedule creation with all schedule types
- Test schedule creation with max_repetitions
- Test error handling for database insertion failures
- Test unified reminder creation via CLI adapter

#### Function: `list_schedules()`
- Test listing with agent_id filter
- Test listing with active_only filter
- Test conversion from unified format to CLI format
- Test error handling for database query failures

#### Function: `get_schedule()`
- Test retrieval of existing schedules
- Test handling of non-existent schedules
- Test CLI format conversion

#### Function: `update_schedule()`
- Test schedule field updates
- Test field mapping between CLI and unified formats
- Test error handling for update failures

#### Function: `cancel_schedule()`
- Test schedule deactivation
- Test error handling for cancellation failures

#### Function: `get_due_schedules()`
- Test retrieval of due schedules
- Test filtering by active status and next_run
- Test error handling for query failures

#### Function: `cleanup_old_schedules()`
- Test cleanup of old inactive schedules
- Test age-based filtering
- Test CLI-only reminder cleanup (avoiding web reminders)
- Test error handling for cleanup operations

#### Function: `get_database_stats()`
- Test statistics collection for monitoring
- Test CLI vs web reminder counting
- Test error handling for statistics collection

### promptyoself_mcp_server.py

#### MCP Tool Functions
- Test `promptyoself_register()` parameter validation and error handling
- Test `promptyoself_list()` filtering options
- Test `promptyoself_cancel()` ID validation
- Test `promptyoself_execute()` execution modes
- Test `promptyoself_test()` connectivity testing
- Test `promptyoself_agents()` agent listing
- Test `promptyoself_upload()` authentication requirements

#### Function: `health()`
- Test health check response format
- Test configuration reporting
- Test authentication status reporting

#### Server Initialization
- Test STDIO transport initialization
- Test HTTP transport initialization
- Test SSE transport initialization
- Test error handling for transport failures

## Test Coverage Strategy

1. **Unit Tests**: Focus on individual function testing with mocked dependencies
2. **Integration Tests**: Test interactions between modules with real database
3. **Error Condition Testing**: Cover all error paths and exception handling
4. **Edge Case Testing**: Test boundary conditions and unusual inputs
5. **Concurrency Testing**: Test scheduler thread safety and database locking

## Estimated Test Count

- **`letta_api.py`**: 35-40 test cases
- **`cli.py`**: 45-50 test cases  
- **`scheduler.py`**: 25-30 test cases
- **`db.py`**: 30-35 test cases
- **`mcp_server.py`**: 15-20 test cases

**Total Estimated Tests:** 150-175 new test cases

## Implementation Priority

1. **Critical Path Tests** (API integration, database operations)
2. **Error Handling Tests** (all error conditions and exceptions)
3. **Edge Case Tests** (boundary conditions, unusual inputs)
4. **Concurrency Tests** (scheduler thread safety)

This test plan provides comprehensive coverage of all currently untested functionality and will significantly improve test coverage from 26.27% to over 80% when implemented.