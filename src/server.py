"""WebSocket server for Claw2Cline."""
import asyncio
import json
import logging
from typing import Dict, Optional
import websockets
from websockets.server import serve
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
        self.process: Optional[asyncio.subprocess.Process] = None
        self.output = ""
        self.status = TaskStatus.EXECUTING

    async def run(self) -> None:
        """Execute the Cline command."""
        try:
            logger.info(f"Starting task {self.request.id}: {self.request.command}")
            self.process = await asyncio.create_subprocess_shell(
                self.request.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            # Read output
            stdout, _ = await self.process.communicate()
            self.output = stdout.decode("utf-8", errors="replace")

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
        self.clients = set()

    async def handle_connection(self, websocket, path: str) -> None:
        """Handle a WebSocket connection."""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"Client connected: {client_addr}")

        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_addr}")
        finally:
            self.clients.discard(websocket)

    async def handle_message(self, websocket, message: str) -> None:
        """Handle an incoming message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == MessageType.TASK.value:
                request = TaskRequest.from_dict(data)
                await self.handle_task(websocket, request)
            elif msg_type == MessageType.HEARTBEAT.value:
                await websocket.send(json.dumps({"type": "heartbeat", "status": "ok"}))
            else:
                logger.warning(f"Unknown message type: {msg_type}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def handle_task(self, websocket, request: TaskRequest) -> None:
        """Handle a task request."""
        # Send immediate acknowledgment
        ack = create_task_response(
            request.id, TaskStatus.EXECUTING, "Task started"
        )
        await websocket.send(ack.to_json())
        
        # Create and run task
        task = ClineTask(request)
        self.tasks[request.id] = task
        
        # Run task in background
        asyncio.create_task(self.run_task(websocket, task))

    async def run_task(self, websocket, task: ClineTask) -> None:
        """Run a task and send result when complete."""
        await task.run()
        
        # Send result
        response = create_task_response(
            task.request.id, task.status, task.output
        )
        await websocket.send(response.to_json())
        
        # Clean up
        self.tasks.pop(task.request.id, None)

    async def start(self) -> None:
        """Start the server."""
        logger.info(f"Starting server on {self.host}:{self.port}")
        
        async with serve(self.handle_connection, self.host, self.port):
            logger.info(f"Server listening on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever

    async def stop(self) -> None:
        """Stop the server."""
        logger.info("Stopping server")
        # Cancel all running tasks
        for task_id in list(self.tasks.keys()):
            logger.info(f"Cancelling task {task_id}")

def main():
    """Main entry point for server."""
    server = Server()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()