# Testing Guide

**Version: 2.2.0**

This document provides comprehensive information about the testing infrastructure for Sanctum Letta MCP, including how to run tests, understand test coverage, and contribute to the test suite.

## 🧪 Test Overview

The project includes a comprehensive testing infrastructure with three main test types:

- **Unit Tests** - Test individual functions and components in isolation
- **Integration Tests** - Test HTTP endpoints and SSE connections
- **End-to-End Tests** - Test complete workflows with real plugins

## 🚀 Quick Start

### Running All Tests

```bash
# Run all tests with coverage
python run_tests.py --type all --coverage

# Run all tests without coverage
python run_tests.py --type all
```

### Running Specific Test Types

```bash
# Unit tests only
python run_tests.py --type unit

# Integration tests only
python run_tests.py --type integration

# End-to-end tests only
python run_tests.py --type e2e
```

### Direct Pytest Usage

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run with coverage
python -m pytest --cov=mcp

# Run specific test file
python -m pytest tests/unit/test_plugin_discovery.py

# Run tests matching a pattern
python -m pytest -k "plugin"
```

## 📁 Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_plugin_discovery.py
│   ├── test_plugin_execution.py
│   ├── test_tools_manifest.py
│   └── test_plugins/        # Plugin-specific tests
│       ├── test_botfather_plugin.py
│       └── test_devops_plugin.py
├── integration/             # Integration tests
│   ├── test_http_endpoints.py
│   └── test_sse_endpoint.py
└── e2e/                     # End-to-end tests
    └── test_full_workflow.py
```

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)

```ini
[tool:pytest]
asyncio_mode = strict
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
timeout = 300
addopts = 
    --strict-markers
    --disable-warnings
```

### Test Runner (`run_tests.py`)

The test runner provides a convenient interface for running different test types:

```bash
python run_tests.py --help
```

**Options:**
- `--type {unit,integration,e2e,all,coverage}` - Test type to run
- `--verbose` - Verbose output
- `--no-cov` - Disable coverage reporting

## 🧩 Test Types

### Unit Tests

Unit tests focus on testing individual functions and components in isolation.

**Location:** `tests/unit/`

**Key Test Files:**
- `test_plugin_discovery.py` - Tests plugin discovery logic
- `test_plugin_execution.py` - Tests plugin execution
- `test_tools_manifest.py` - Tests tools manifest building
- `test_plugins/` - Plugin-specific unit tests

**Example Unit Test:**

```python
@pytest.mark.asyncio
async def test_discover_plugins():
    """Test plugin discovery functionality."""
    plugins = discover_plugins()
    assert isinstance(plugins, dict)
    assert "botfather" in plugins
    assert "devops" in plugins
```

### Integration Tests

Integration tests verify that different components work together correctly.

**Location:** `tests/integration/`

**Key Test Files:**
- `test_http_endpoints.py` - Tests HTTP endpoints
- `test_sse_endpoint.py` - Tests SSE connections

**Example Integration Test:**

```python
@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health endpoint returns correct data."""
    async with client.get('/health') as response:
        assert response.status == 200
        data = await response.json()
        assert "status" in data
        assert data["status"] == "healthy"
```

### End-to-End Tests

E2E tests verify complete workflows with real plugins and actual server interactions.

**Location:** `tests/e2e/`

**Key Test Files:**
- `test_full_workflow.py` - Complete workflow scenarios

**Example E2E Test:**

```python
@pytest.mark.asyncio
async def test_complete_plugin_workflow(client, temp_plugins_dir_with_plugins):
    """Test complete workflow from plugin discovery to execution."""
    # Test health check
    async with client.get('/health') as response:
        health_data = await response.json()
        assert health_data["plugins"] == 1

    # Test SSE connection
    async with client.get('/sse') as response:
        assert response.status == 200
        # ... test tools manifest

    # Test plugin execution
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "workflow_test_plugin.workflow-command",
            "arguments": {"param": "test_value"}
        }
    }
    async with client.post('/message', json=request) as response:
        assert response.status == 200
        # ... verify response
```

## 🔧 Test Fixtures

### Core Fixtures (`conftest.py`)

**`client`** - aiohttp TestClient instance
```python
@pytest.fixture
async def client():
    """Create a test client for the application."""
    app = await init_app()
    return TestClient(app)
```

**`temp_plugins_dir`** - Temporary directory for test plugins
```python
@pytest.fixture
def temp_plugins_dir():
    """Create a temporary directory for test plugins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugins_dir = Path(temp_dir) / "plugins"
        plugins_dir.mkdir()
        yield plugins_dir
```

**`temp_plugins_dir_with_plugins`** - Temporary directory with test plugins
```python
@pytest.fixture
def temp_plugins_dir_with_plugins(request):
    """Create temporary plugins directory with test plugins."""
    plugins = request.param
    with tempfile.TemporaryDirectory() as temp_dir:
        plugins_dir = Path(temp_dir) / "plugins"
        plugins_dir.mkdir()
        
        # Create test plugins
        for plugin in plugins:
            plugin_dir = plugins_dir / plugin['name']
            plugin_dir.mkdir()
            
            cli_path = plugin_dir / "cli.py"
            with open(cli_path, 'w') as f:
                f.write(plugin['cli_content'])
            
            os.chmod(cli_path, 0o755)
        
        # Set environment variable for plugin discovery
        os.environ['MCP_PLUGINS_DIR'] = str(plugins_dir)
        
        yield plugins_dir
        
        # Cleanup
        if 'MCP_PLUGINS_DIR' in os.environ:
            del os.environ['MCP_PLUGINS_DIR']
```

## 📊 Coverage Reporting

### Running Coverage

```bash
# Run with coverage
python run_tests.py --type all --coverage

# Generate HTML coverage report
python -m pytest --cov=mcp --cov-report=html
```

### Coverage Configuration

Coverage is configured in `pytest.ini`:

```ini
[tool:pytest]
addopts = 
    --cov=mcp
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
```

### Coverage Targets

- **Minimum Coverage:** 80%
- **Target Coverage:** 90%+
- **Critical Paths:** 100% (plugin discovery, execution, error handling)

## ⏱️ Timeout Protection

All tests include timeout protection to prevent hanging:

```python
@pytest.mark.timeout(60)  # 60 second timeout
async def test_long_running_operation():
    # Test implementation
    pass
```

**Timeout Guidelines:**
- Unit tests: 10-30 seconds
- Integration tests: 30-60 seconds
- E2E tests: 45-120 seconds

## 🐛 Debugging Tests

### Verbose Output

```bash
# Run with verbose output
python -m pytest -v

# Run with maximum verbosity
python -m pytest -vvv
```

### Debugging Specific Tests

```bash
# Run single test with output
python -m pytest tests/unit/test_plugin_discovery.py::test_discover_plugins -v -s

# Run with debugger
python -m pytest tests/unit/test_plugin_discovery.py::test_discover_plugins --pdb
```

### Logging in Tests

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

@pytest.mark.asyncio
async def test_with_logging():
    logger = logging.getLogger(__name__)
    logger.debug("Debug information")
    # Test implementation
```

## 🧪 Writing Tests

### Test Naming Conventions

- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

### Test Structure

```python
@pytest.mark.asyncio
async def test_function_name():
    """Test description."""
    # Arrange
    # Set up test data and conditions
    
    # Act
    # Execute the function being tested
    
    # Assert
    # Verify the results
```

### Best Practices

1. **Isolation:** Each test should be independent
2. **Descriptive Names:** Test names should clearly describe what they test
3. **Single Responsibility:** Each test should test one thing
4. **Clean Setup/Teardown:** Use fixtures for setup and cleanup
5. **Meaningful Assertions:** Assertions should be specific and meaningful

### Example Test Template

```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_plugin_execution_success():
    """Test successful plugin execution."""
    # Arrange
    tool_name = "test_plugin.test_command"
    arguments = {"param": "value"}
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"result": "success"}'
        
        # Act
        result = await execute_plugin_tool(tool_name, arguments)
        
        # Assert
        assert "result" in result
        assert result["result"] == "success"
        mock_run.assert_called_once()
```

## 🔄 Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          python run_tests.py --type all --coverage
```

## 📈 Performance Testing

### Load Testing

For high-concurrency scenarios, consider adding load tests:

```python
@pytest.mark.asyncio
async def test_concurrent_connections(client):
    """Test handling of multiple concurrent SSE connections."""
    connections = []
    
    # Create multiple connections
    for i in range(10):
        response = await client.get('/sse')
        assert response.status == 200
        connections.append(response)
    
    # Verify all connections work
    for conn in connections:
        data = await conn.content.readline()
        assert data is not None
```

## 🚨 Common Issues

### Test Failures

1. **Import Errors:** Ensure all dependencies are installed
2. **Timeout Errors:** Increase timeout or optimize slow tests
3. **Environment Issues:** Check environment variables and paths
4. **Async Issues:** Ensure proper async/await usage

### Debugging Tips

1. **Check Logs:** Look at test output for error messages
2. **Isolate Tests:** Run individual tests to identify issues
3. **Check Dependencies:** Ensure all required packages are installed
4. **Environment:** Verify environment variables and paths

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [aiohttp Testing](https://docs.aiohttp.org/en/stable/testing.html)
- [Python Testing Best Practices](https://realpython.com/python-testing/)

---

**Note:** This testing infrastructure ensures the reliability and maintainability of the Sanctum Letta MCP server. All new features should include appropriate tests. 