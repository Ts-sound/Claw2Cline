"""WebSocket server for Claw2Cline using threading."""

import json
import logging
import subprocess
import threading
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


class ClineTask:
    """Represents a running Cline task."""

    def __init__(self, request: TaskRequest):
        self.request = request
        self.process = None
        self.output = ""
        self.status = TaskStatus.EXECUTING
        self.lock = threading.Lock()

    def run(self) -> None:
        """Execute the Cline command."""
        try:
            logger.info(f"Starting task {self.request.id}: {self.request.command}")
            self.process = subprocess.Popen(
                self.request.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            # Read output
            stdout, _ = self.process.communicate()
            self.output = stdout

            if self.process.returncode == 0:
                self.status = TaskStatus.SUCCESS
                logger.info(f"Task {self.request.id} completed successfully")
            else:
                self.status = TaskStatus.FAILED
                logger.warning(f"Task {self.request.id} failed with code {self.process.returncode}")
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
        if not task_id:
            error_response = create_task_response("", TaskStatus.FAILED, "Missing task_id in request")
            from websocket_server import WebsocketServer
            server.send_message(client, error_response.to_json())
            return

        if task_id in self.tasks:
            task = self.tasks[task_id]
            response = create_task_response(task_id, task.status, task.output)
            from websocket_server import WebsocketServer
            server.send_message(client, response.to_json())
        else:
            # Task not found, could be completed
            # Return a completed status or indicate task not found
            response = create_task_response(task_id, TaskStatus.SUCCESS, "Task completed or not found")
            from websocket_server import WebsocketServer
            server.send_message(client, response.to_json())

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
