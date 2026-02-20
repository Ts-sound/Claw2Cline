"""WebSocket server for Claw2Cline using threading."""

import json
import logging
import subprocess
import threading
import os
import glob
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import websocket
from .config import config
from .protocol import (
    TaskRequest,
    TaskResponse,
    TaskStatus,
    MessageType,
    create_task_response,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default workspace directory
WORKSPACE_DIR = "/opt/tong/ws/git-repo"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClineTask:
    """Represents a running Cline task."""

    def __init__(self, request: TaskRequest):
        self.request = request
        self.process = None
        self.output = ""
        self.status = TaskStatus.EXECUTING
        self.lock = threading.Lock()

    def _parse_project_from_command(self, command: str) -> str:
        """
        Parse the project name from command to determine working directory.
        Looks for patterns like: cline -y -c "/path/to/project" "command"
        or tries to identify project from the command structure.
        """
        import re
        
        # Look for the -c flag followed by a project directory
        # Pattern: -c "/path/to/project" or -c '/path/to/project'
        cline_pattern = r'-c\s+[\'"]([^\'"]+)[\'"]'
        matches = re.findall(cline_pattern, command)
        
        if matches:
            project_path = matches[0]
            # Extract project name from path
            project_name = os.path.basename(project_path)
            return project_name
        
        # If no -c flag found, try to identify from workspace
        # If the command contains workspace references, extract project
        workspace_matches = re.findall(r'/opt/tong/ws/git-repo/([^/\s]+)', command)
        if workspace_matches:
            return workspace_matches[0]
        
        # Default: return current project name (current directory name)
        return os.path.basename(os.getcwd())

    def _get_project_directory(self, project_name: str) -> str:
        """Get the full path to the project directory."""
        project_path = os.path.join(WORKSPACE_DIR, project_name)
        
        # Check if the project directory exists
        if os.path.isdir(project_path):
            return project_path
        else:
            # If project doesn't exist in workspace, return default project (current)
            logger.warning(f"Project '{project_name}' not found in workspace. Using current directory.")
            return os.getcwd()

    def run(self) -> None:
        """Execute the Cline command in the appropriate project directory."""
        try:
            # Determine the project directory based on the command
            project_name = self._parse_project_from_command(self.request.command)
            project_dir = self._get_project_directory(project_name)
            
            logger.info(f"Starting task {self.request.id}: {self.request.command}")
            logger.info(f"Project directory: {project_dir}")
            
            # Execute command in the project directory
            self.process = subprocess.Popen(
                self.request.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=project_dir  # Set working directory to project directory
            )
            
            # Read output
            stdout, _ = self.process.communicate()
            self.output = stdout

            if self.process.returncode == 0:
                self.status = TaskStatus.SUCCESS
                logger.info(f"Task {self.request.id} completed successfully in {project_dir}")
            else:
                self.status = TaskStatus.FAILED
                logger.warning(f"Task {self.request.id} failed with code {self.process.returncode} in {project_dir}")
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.output = str(e)
            logger.error(f"Task {self.request.id} error: {e}")


class Server:
    """WebSocket server for handling task requests."""

    def __init__(self, host: str = None, port: int = None):
        self.host = host or config.server_host
        self.port = port or config.server_port
        self.tasks: Dict[str, ClineTask] = {}
        self.clients = []  # Use list instead of set since client objects are not hashable
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.ws_server = None

    def start(self) -> None:
        """Start the server."""
        logger.info(f"Starting server on {self.host}:{self.port}")
        
        from websocket_server import WebsocketServer
        self.ws_server = WebsocketServer(host=self.host, port=self.port)
        self.ws_server.set_fn_new_client(self.handle_new_client)
        self.ws_server.set_fn_message_received(self.message_received)
        self.ws_server.run_forever()
    
    def handle_new_client(self, client, server) -> None:
        """Handle a new client connection."""
        # Add client to our list
        self.clients.append(client)
        logger.info(f"New client connected")

    def message_received(self, client, server, message) -> None:
        """Handle an incoming message from a client."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == MessageType.TASK.value:
                request = TaskRequest.from_dict(data)
                logger.info(f"Received task request {request.id} from client")
                self.handle_task(client, server, request)
            elif msg_type == MessageType.HEARTBEAT.value:
                from websocket_server import WebsocketServer
                server.send_message(client, json.dumps({"type": "heartbeat", "status": "ok"}))
            elif msg_type == MessageType.GET_TASK_STATUS.value:
                self.handle_get_task_status(client, server, data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def handle_task(self, client, server, request: TaskRequest) -> None:
        """Handle a task request."""
        # Send immediate acknowledgment
        ack = create_task_response(request.id, TaskStatus.EXECUTING, "Task started")
        from websocket_server import WebsocketServer
        server.send_message(client, ack.to_json())

        # Create and run task
        task = ClineTask(request)
        self.tasks[request.id] = task

        # Run task in background thread
        self.executor.submit(self.run_task, client, server, task)

    def handle_get_task_status(self, client, server, data: dict) -> None:
        """Handle a task status query."""
        task_id = data.get("task_id")
        logger.info(f"Received status query for task: {task_id}")
        
        if not task_id:
            error_response = create_task_response("", TaskStatus.FAILED, "Missing task_id in request")
            from websocket_server import WebsocketServer
            server.send_message(client, error_response.to_json())
            logger.warning(f"Status query received without task_id: {data}")
            return

        if task_id in self.tasks:
            task = self.tasks[task_id]
            response = create_task_response(task_id, task.status, task.output)
            from websocket_server import WebsocketServer
            server.send_message(client, response.to_json())
            logger.info(f"Status query responded - Task: {task_id}, Status: {task.status}, Output length: {len(task.output)}")
        else:
            # Task not found, could be completed
            # Return a completed status or indicate task not found
            response = create_task_response(task_id, TaskStatus.SUCCESS, "Task completed or not found")
            from websocket_server import WebsocketServer
            server.send_message(client, response.to_json())
            logger.info(f"Status query responded - Task not found: {task_id}, returning completed status")

    def run_task(self, client, server, task: ClineTask) -> None:
        """Run a task and send result when complete."""
        task.run()

        # Send final result
        response = create_task_response(task.request.id, task.status, task.output)
        try:
            from websocket_server import WebsocketServer
            server.send_message(client, response.to_json())
            logger.info(f"Sent result for task {task.request.id} to client")
        except:
            # Client may have disconnected, just log the error
            logger.warning(f"Could not send result to client, connection closed for task {task.request.id}")

        # Clean up
        self.tasks.pop(task.request.id, None)

    def stop(self) -> None:
        """Stop the server."""
        logger.info("Stopping server")
        # Shutdown executor
        self.executor.shutdown(wait=True)
        # Cancel all running tasks
        for task_id in list(self.tasks.keys()):
            logger.info(f"Cancelling task {task_id}")


def main():
    """Main entry point for server."""
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        server.stop()


if __name__ == "__main__":
    main()
