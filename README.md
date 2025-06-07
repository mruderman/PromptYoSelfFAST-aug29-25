# Sanctum Letta MCP

Internal tools orchestration server for managing command-line tools and automation scripts.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration:
```bash
cp .env.example .env
# Edit .env with your settings
```

## Running the Server

```bash
uvicorn mcp.main:app --reload
```

## Running Tests

```bash
pytest
```

## Project Structure

- `mcp/` - Main package
  - `main.py` - FastAPI application entry point
  - `plugins/` - Plugin implementations
  - `queue/` - Job queue implementation
  - `models/` - Pydantic models
  - `config.py` - Configuration management
  - `logger.py` - Logging setup

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc 

## License

This project is licensed under the Creative Commons Attribution-ShareAlike (CC BY-SA) license. See LICENSE for details. 