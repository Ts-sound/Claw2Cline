"""Client daemon for Claw2Cline using threading."""

import json
import logging
import os
import signal
import sys
import time
import threading
from pathlib import Path
import websocket
from .config import config
from .protocol import (
    TaskRequest,
    TaskResponse,
    TaskStatus,
    MessageType,
    create_task_request,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClientDaemon:
    """Client daemon that bridges named pipes and WebSocket."""

    def __init__(self):
        self.websocket = None
        self.running = False
        self.request_pipe: Path = config.request_pipe_path
        self.response_pipe: Path = config.response_pipe_path
        self.pid_file: Path = config.pid_file_path
        self.active_tasks = {}  # Track active tasks that need polling
        self.workspace_dir: str = ""  # Workspace directory from server
        logger.info("ClientDaemon initialized")

    def setup(self) -> None:
        """Setup named pipes and directories."""
        config.ensure_cache_dir()

        # Create named pipes if they don't exist
        for pipe_path in [self.request_pipe, self.response_pipe]:
            if not pipe_path.exists():
                os.mkfifo(str(pipe_path))
                logger.info(f"Created pipe: {pipe_path}")

        # Write PID file
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))
        logger.info(f"Wrote PID {os.getpid()} to {self.pid_file}")

    def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("Cleaning up...")

        # Remove pipes
        for pipe_path in [self.request_pipe, self.response_pipe]:
            if pipe_path.exists():
                pipe_path.unlink()
                logger.info(f"Removed pipe: {pipe_path}")

        # Remove PID file
        if self.pid_file.exists():
            self.pid_file.unlink()
            logger.info(f"Removed PID file: {self.pid_file}")

    def connect_server(self) -> None:
        """Connect to WebSocket server and get workspace directory."""
        server_url = config.server_url
        logger.info(f"Connecting to server: {server_url}")

        max_retries = 10
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                self.websocket = websocket.WebSocket()
                self.websocket.connect(server_url)
                logger.info("Connected to server")
                
                # Query workspace directory from server
                self.send_workspace_query()
                
                # Wait for workspace response (with timeout)
                start_time = time.time()
                while time.time() - start_time < 5 and not self.workspace_dir:
                    message = self.websocket.recv()
                    data = json.loads(message)
                    if data.get("type") == "workspace_status":
                        self.workspace_dir = data.get("workspace_dir", "")
                        logger.info(f"Got workspace directory from server: {self.workspace_dir}")
                        break
                
                if not self.workspace_dir:
                    logger.warning("Failed to get workspace directory from server")
                
                return
            except Exception as e:
                logger.error(f"Failed to connect to server (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30 seconds
                else:
                    logger.error("Max retries reached, giving up")
                    raise

    def send_status_query(self, task_id: str) -> None:
        """Send a status query for a specific task."""
        try:
            status_query = {"type": MessageType.GET_TASK_STATUS.value, "task_id": task_id, "timestamp": int(time.time())}
            if self.websocket:
                self.websocket.send(json.dumps(status_query))
                logger.info(f"Status query sent - Task: {task_id}, Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
            else:
                logger.warning(f"Cannot send status query - WebSocket not connected for task: {task_id}")
        except Exception as e:
            logger.error(f"Failed to send status query for task {task_id}: {str(e)}")
            logger.debug(f"Status query payload: {status_query}", exc_info=True)

    def send_workspace_query(self) -> None:
        """Send workspace status query to server."""
        try:
            query = {"type": MessageType.WORKSPACE_QUERY.value}
            if self.websocket:
                self.websocket.send(json.dumps(query))
                logger.info("Sent workspace query to server")
            else:
                logger.warning("Cannot send workspace query - WebSocket not connected")
        except Exception as e:
            logger.error(f"Failed to send workspace query: {str(e)}")

    def send_projects_query(self) -> None:
        """Send projects list query to server."""
        try:
            query = {"type": MessageType.PROJECTS_QUERY.value}
            if self.websocket:
                self.websocket.send(json.dumps(query))
                logger.info("Sent projects query to server")
            else:
                logger.warning("Cannot send projects query - WebSocket not connected")
        except Exception as e:
            logger.error(f"Failed to send projects query: {str(e)}")

    def poll_task_status_thread(self, task_id: str) -> None:
        """Thread function to poll for task status every 5 seconds."""
        logger.info(f"Polling for status of task: {task_id}")
        while self.running and task_id in self.active_tasks:
            time.sleep(5)  # Poll every 5 seconds
            self.send_status_query(task_id)

    def start_task_polling(self, task_id: str) -> None:
        """Start polling for a specific task's status."""
        logger.info(f"Starting polling for task: {task_id}")
        if task_id not in self.active_tasks:
            self.active_tasks[task_id] = True
            # Start the polling thread in the background
            poll_thread = threading.Thread(target=self.poll_task_status_thread, args=(task_id,))
            poll_thread.daemon = True
            poll_thread.start()
            logger.info(f"Started polling thread for task: {task_id}")

    def read_request_pipe(self) -> None:
        """Read from request pipe and send to WebSocket."""
        logger.info(f"Listening on request pipe: {self.request_pipe}")

        while self.running:
            try:
                # Open pipe for reading (blocks until writer opens)
                with open(self.request_pipe, "r") as pipe:
                    while self.running:
                        line = pipe.readline()
                        if not line:
                            break
                        line = line.strip()
                        if not line:
                            continue
                        logger.info(f"Received from pipe: {line}")

                        # Parse the command
                        # Format: "send [session] [--project project_name] <command>"
                        # Or: "workspace" or "projects"
                        parts = line.split(maxsplit=1)
                        if len(parts) < 1:
                            logger.warning(f"Invalid command format: {line}")
                            continue

                        # Handle workspace query
                        if parts[0] == "workspace":
                            self.send_workspace_query()
                            continue

                        # Handle projects query
                        if parts[0] == "projects":
                            self.send_projects_query()
                            continue

                        # Handle send command
                        if parts[0] == "send":
                            # Parse the full line with more parts to capture all arguments
                            all_parts = line.split()
                            if len(all_parts) < 2:
                                logger.warning(f"Invalid command format: {line}")
                                continue

                            # Parse session, optional project, and command
                            idx = 1
                            session = "default"
                            project = None

                            # Check if next part is session or --project
                            if idx < len(all_parts) and not all_parts[idx].startswith("--"):
                                session = all_parts[idx]
                                idx += 1

                            # Check for --project flag
                            if idx < len(all_parts) and all_parts[idx] == "--project":
                                idx += 1
                                if idx < len(all_parts):
                                    project = all_parts[idx]
                                    idx += 1

                            # Get the rest as command (may contain spaces)
                            command = " ".join(all_parts[idx:]) if idx < len(all_parts) else ""

                            # Build command with project info if specified
                            if project:
                                # Build full path using workspace_dir from server
                                if self.workspace_dir:
                                    project_path = os.path.join(self.workspace_dir, project)
                                else:
                                    # Fallback to project name if workspace_dir not set
                                    project_path = project
                                # Command must be quoted to preserve arguments
                                full_command = f'cline -y -c "{project_path}" "{command}"'
                            else:
                                full_command = command

                            # Create and send task request
                            request = create_task_request(full_command, session)
                            if self.websocket:
                                self.websocket.send(request.to_json())
                                logger.info(f"Sent task {request.id} to server (project: {project})")

                                # Start polling for this task's status
                                self.start_task_polling(request.id)
                        else:
                            logger.warning(f"Unknown command: {parts[0]}")
            except FileNotFoundError:
                logger.error(f"Request pipe not found: {self.request_pipe}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error reading request pipe: {e}")
                time.sleep(1)

    def response_to_text(self, response_json: str) -> str:
        """Convert JSON response to text format with newlines."""
        try:
            data = json.loads(response_json)
            lines = []
            for key, value in data.items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)
        except json.JSONDecodeError:
            return response_json

    def write_response_pipe(self, response: str) -> None:
        """Write response to response pipe in text format."""
        try:
            # Convert JSON to text format
            text_response = self.response_to_text(response)
            with open(self.response_pipe, "w") as pipe:
                pipe.write(text_response + "\n")
                pipe.flush()
            logger.info(f"Wrote response to pipe")
        except Exception as e:
            logger.error(f"Error writing response pipe: {e}")

    def listen_websocket(self) -> None:
        """Listen for WebSocket messages."""
        logger.info("Listening for WebSocket messages")

        try:
            while self.running:
                message = self.websocket.recv()
                logger.info(f"Received from server: {message}")

                # Parse response
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == MessageType.STATUS.value:
                        response = TaskResponse.from_dict(data)

                        # Check if this is a final status (success or failed)
                        if response.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
                            # Stop polling for this task since it's complete
                            task_id = response.id
                            if task_id in self.active_tasks:
                                del self.active_tasks[task_id]
                                logger.info(f"Stopped polling for completed task: {task_id}")

                        # Write to response pipe
                        self.write_response_pipe(message)
                        logger.info(f"Output: {data.get('output')}")
                    elif msg_type == "workspace_status":
                        # Write workspace response to pipe
                        self.write_response_pipe(message)
                        logger.info(f"Workspace status: {data}")
                    elif msg_type == "projects_list":
                        # Write projects response to pipe
                        self.write_response_pipe(message)
                        logger.info(f"Projects list: {data}")
                    else:
                        logger.info(f"Received message type: {msg_type}")

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from server: {message}")
        except websocket.WebSocketConnectionClosedException:
            logger.warning("WebSocket connection closed")
            self.running = False
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.running = False

    def run(self) -> None:
        """Main run loop."""
        self.running = True
        try:
            self.setup()
            self.connect_server()

            # Run both tasks concurrently using threads
            request_thread = threading.Thread(target=self.read_request_pipe)
            websocket_thread = threading.Thread(target=self.listen_websocket)

            request_thread.daemon = True
            websocket_thread.daemon = True

            request_thread.start()
            websocket_thread.start()

            # Wait for threads to complete (they run indefinitely)
            request_thread.join()
            websocket_thread.join()

        finally:
            self.cleanup()

    def stop(self) -> None:
        """Stop the daemon."""
        logger.info("Stopping client daemon")
        self.running = False
        if self.websocket:
            self.websocket.close()


def main():
    """Main entry point for client daemon."""
    daemon = ClientDaemon()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")
        daemon.stop()


if __name__ == "__main__":
    main()
