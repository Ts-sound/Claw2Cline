
# Technical Context

## Technologies Used

### Primary Language
- **Python**: Core implementation language for the bridge

### Communication
- **WebSocket**: Real-time bi-directional communication protocol
- **JSON**: Message format for task dispatch and status updates

### External Systems
- **Cline CLI**: Target system for task execution
- **OpenClaw**: Source system for task delegation
- **openclaw agent**: CLI command for notification callback

## Development Setup

### Prerequisites
- Python 3.8+ (for asyncio and modern async features)
- pip or poetry for dependency management
- Access to Cline CLI
- Access to OpenClaw agent CLI

### Recommended Project Structure

```bash
Claw2Cline/
├── src/
│   ├── __init__.py
│   ├── server.py    # WebSocket server
│   ├── client.py    # WebSocket client
│   ├── executor.py  # Cline CLI executor
│   ├── notifier.py  # OpenClaw notification
│   └── config.py    # Configuration management
├── tests/
│   ├── __init__.py
│   ├── test_server.py
│   ├── test_client.py
│   └── test_executor.py
├── pyproject.toml   # Project metadata and dependencies
├── README.md
└── LICENSE
```

## Technical Constraints
1. **Async Requirements**: Must use async/await for non-blocking operations
2. **Process Isolation**: Cline CLI runs in separate subprocess
3. **Connection Reliability**: Must handle WebSocket disconnections gracefully
4. **Resource Management**: Proper cleanup of subprocesses on shutdown

## Dependencies (Planned)

| Package          | Purpose                                      |
|------------------|----------------------------------------------|
| websockets       | WebSocket server/client implementation       |
| asyncio          | Async runtime (stdlib)                       |
| subprocess       | CLI execution (stdlib)                       |
| pydantic         | Data validation and settings management      |
| pytest           | Testing framework                            |
| pytest-asyncio   | Async test support                           |

## Tool Usage Patterns

### WebSocket Library Options
- `websockets`: Lightweight, pure Python, well-maintained
- `aiohttp`: Full-featured HTTP/WebSocket server
- Recommendation: Start with `websockets` for simplicity

### Subprocess Management
- Use `asyncio.create_subprocess_exec()` for async subprocess
- Capture stdout/stderr for result reporting
- Implement timeout handling for long-running tasks

### Configuration
- Environment variables for sensitive data
- YAML or TOML for application config
- pydantic for validation