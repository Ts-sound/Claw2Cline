
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
- Python 3.8+
- pip or poetry for dependency management
- Access to Cline CLI
- Access to OpenClaw agent CLI

### Recommended Project Structure

```bash
Claw2Cline/
├── src/
│   ├── __init__.py
│   ├── server.py    # WebSocket server
│   ├── clientd.py   # WebSocket client daemon
│   ├── protocol.py  # Message protocol definitions
│   ├── cli.py       # Command line interface
│   └── config.py    # Configuration management
├── tests/
│   ├── __init__.py
│   ├── test_server.py
│   ├── test_clientd.py
│   ├── test_protocol.py
│   └── test_cli.py
├── pyproject.toml   # Project metadata and dependencies
├── README.md
└── LICENSE
```

## Technical Constraints
1. **Threading Model**: Must use threading for non-blocking operations (replaced async/await)
2. **Process Isolation**: Cline CLI runs in separate subprocess
3. **Connection Reliability**: Must handle WebSocket disconnections gracefully
4. **Resource Management**: Proper cleanup of subprocesses and threads on shutdown

## Dependencies (Current)

| Package          | Purpose                                      |
|------------------|----------------------------------------------|
| websocket-client | WebSocket client implementation              |
| websocket-server | WebSocket server implementation              |
| subprocess       | CLI execution (stdlib)                       |
| threading        | Concurrent operation support (stdlib)        |
| pytest           | Testing framework                            |

## Tool Usage Patterns

### WebSocket Library Options
- `websocket-client`: Client-side WebSocket implementation
- `websocket-server`: Server-side WebSocket implementation
- Replaced `websockets` library with threading-based approach

### Subprocess Management
- Use `subprocess.Popen()` for synchronous subprocess execution
- Capture stdout/stderr for result reporting
- Implement timeout handling for long-running tasks

### Threading Model
- Use `threading` module for concurrent operations
- Use `ThreadPoolExecutor` for managing worker threads
- Implement proper synchronization for shared resources

### Configuration
- Environment variables for sensitive data
- YAML or TOML for application config
- Custom config management in config.py

### Workspace and Project Management
- **Purpose**: Support for managing multiple projects in a workspace directory (`/opt/tong/ws/git-repo`)
- **Commands**: `claw2cline workspace`, `claw2cline projects`, `claw2cline send --project <project>`
- **Project Detection**: Identifies projects by common indicators like `.git`, `README.md`, `package.json`, `setup.py`, etc.
- **Directory Switching**: Automatically switches to project directory when executing commands with `--project` flag
- **Path Validation**: Validates project paths to prevent security issues
