# Claw2Cline

**Claw2Cline**: A Threading-Based WebSocket Bridge for Orchestrating Cline via OpenClaw Skills.

Claw2Cline is a high-performance Python bridge designed to facilitate seamless task delegation between OpenClaw and Cline. The system has been migrated from an async/await architecture to a threading-based model for better resource control and simpler concurrency management.

By leveraging WebSockets for real-time bi-directional communication, Claw2Cline allows OpenClaw to dispatch complex engineering missions to Cline's CLI. It features a **synchronous execution model** that waits for task completion and returns results through named pipes.

> Claw2Cline is a Python-based orchestration bridge that enables **OpenClaw** to command **Cline** via CLI. It solves the "long-running task" problem in agent collaboration by implementing a **synchronous pipe-based communication pattern**.
> By leveraging **WebSockets** for real-time bi-directional communication, Claw2Cline allows OpenClaw to dispatch complex engineering missions to Cline's CLI. It features a synchronous execution model that waits for task completion and returns results through named pipes.

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Access to Cline CLI
- Access to OpenClaw agent CLI

### Quick Setup

```bash
# Clone the repository
git clone <repository-url>
cd Claw2Cline

# Install the package in development mode
pip install -e .

# Install WebSocket dependencies
pip install websocket-client websocket-server
```

## 🏗️ Architecture Design: WebSocket Forwarding and Notification Mechanism

### 1. Workflow

1. **Dispatch**: OpenClaw triggers a skill to send task JSON via WebSocket to `Claw2Cline`
2. **Acknowledgment**: `Claw2Cline` receives the task and immediately responds with `{"status": "executing"}`, OpenClaw receives the "execution started" reply
3. **Execution**: `Claw2Cline` spawns a Python subprocess to call the Cline CLI command
4. **Notification**: When the Cline task completes, `Claw2Cline` captures the output and executes:
   `openclaw agent --agent main --message "task done: [result]"` for reverse notification

### 2. System Architecture
- **Server Mode**: Manages Cline instances and handles task execution
- **Client Daemon Mode**: Forwards messages from OpenClaw and handles connection management
- **CLI Interface**: Provides command-line access for direct interaction

---

## 📖 Usage Guide

### 1. Starting the Server

```bash
# Start the WebSocket server (typically runs on Cline side)
python -m claw2cline-server
# or
claw2cline-server
```

### 2. Starting the Client Daemon

```bash
# Start the client daemon (typically runs on OpenClaw side)
python -m claw2cline-clientd
# or
claw2cline-clientd
```

### 3. Using the CLI Interface

**Synchronous Mode (Default)**: The `send` command now waits for task completion and returns results through the response pipe.

```bash
# Send a task to Cline (synchronous - waits for completion)
claw2cline send "your command here"

# Send a task with a specific session
claw2cline send --session mysession "your command here"

# Send a task in a specific project directory
claw2cline send --project Claw2Cline "summarize"
claw2cline send -p Claw2Cline "analyze the code"

# Check the status of Claw2Cline
claw2cline status

# Check workspace information
claw2cline workspace

# List all projects in the workspace
claw2cline projects
```

### 4. Workspace and Project Management
The system supports managing multiple projects in a workspace directory (`/opt/tong/ws/git-repo`):

- **Workspace Command**: `claw2cline workspace` - Shows workspace status and available projects **from the server**
- **Projects Command**: `claw2cline projects` - Lists all projects detected in the workspace **on the server**
- **Project-Specific Execution**: Use `--project` or `-p` flag to execute commands in specific project directories
- **Automatic Project Detection**: The system identifies projects by common indicators like `.git`, `README.md`, `package.json`, `setup.py`, etc.
- **Synchronous Execution**: The `send` command waits for task completion and returns results through the response pipe

**Important Note for Remote Access**: All workspace and project commands are executed on the server side, not locally. This means:
- `claw2cline workspace` queries the server for workspace information
- `claw2cline projects` queries the server for project list
- The `--project` flag passes only the project name to the server
- The server resolves the full path in its workspace directory
- This allows seamless remote access without requiring the same directory structure on the client machine

Examples:
- `claw2cline workspace` - Shows server's workspace status
- `claw2cline projects` - Lists projects on the server
- `claw2cline send -p Claw2Cline "summarize"` - Executes command in Claw2Cline project on server (synchronous)

### 4b. Synchronous Execution Model
The `send` command now operates in synchronous mode by default:
- Command is sent through the request pipe
- CLI waits for task completion (up to 60 seconds)
- Results are returned through the response pipe in text format
- Output includes task status (success/failed) and command output

### 4. Named Pipe Integration
The client daemon creates named pipes for seamless integration:
- Request pipe: `/tmp/claw2cline/request.pipe` (default location)
- Response pipe: `/tmp/claw2cline/response.pipe` (default location)

Applications can write commands to the request pipe and read responses from the response pipe.

### 5. Configuration
Configuration is managed through environment variables or the config file:
- `CLAW2CLINE_SERVER_HOST`: Server host (default: localhost)
- `CLAW2CLINE_SERVER_PORT`: Server port (default: 8765)
- `CLAW2CLINE_CACHE_DIR`: Cache directory for named pipes (default: ~/.claw2cline)

---

## ⚙️ Architecture Details

### Threading-Based Model
- **ThreadPoolExecutor**: Manages concurrent task execution with configurable thread pools
- **WebSocket Communication**: Uses websocket-server for server-side and websocket-client for client-side
- **Subprocess Management**: Uses regular subprocess.Popen for task execution (simpler than async subprocess)
- **Thread-Safe Operations**: Proper synchronization for shared resources and state management

### Message Protocol
- **Task Request**: Contains command, session, and metadata
- **Task Response**: Contains status (executing, success, failed), output, and task ID
- **Heartbeat**: Keeps WebSocket connections alive
- **Status Query**: Allows polling for task status

---

## 🔧 Troubleshooting

### Common Issues
1. **WebSocket Connection Issues**: Ensure server is running and firewall allows connections
2. **Named Pipe Errors**: Check permissions and cache directory accessibility
3. **Subprocess Execution**: Verify Cline CLI is accessible in PATH

### Debugging
Enable debug logging by setting environment variable:

```bash
export CLAW2CLINE_LOG_LEVEL=DEBUG
```

---

## 🤝 Integration Examples

### With OpenClaw Skills

```python
# Example of how OpenClaw skills can interact
import subprocess
with open('/tmp/claw2cline/request.pipe', 'w') as pipe:
    pipe.write(f"send mysession echo 'Hello World'\n")
    
# Read response
with open('/tmp/claw2cline/response.pipe', 'r') as pipe:
    response = pipe.read()
```

### Direct API Usage

```python
from src.server import Server
from src.clientd import ClientDaemon

# Programmatically start server
server = Server(host='localhost', port=8765)
server.start()

# Programmatically start client daemon
daemon = ClientDaemon()
daemon.run()
```

```bash
CLAW2CLINE_SERVER_HOST=0.0.0.0 python3 -m src.server

CLAW2CLINE_SERVER_HOST=0.0.0.0 claw2cline-server

CLAW2CLINE_SERVER_URL=ws://172.17.0.2:8765  claw2cline-clientd 
```

## 📋 TODO
- Multi-Cline agent cluster allocation and scheduling
- Enhanced monitoring and metrics
- Advanced task queuing and prioritization
- Improved error recovery mechanisms
