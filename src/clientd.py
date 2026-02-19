"""Client daemon for Claw2Cline."""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
import websockets
from websockets.client import connect
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
        logger.info("ClientDaemon initialized")

    async def setup(self) -> None:
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

    async def cleanup(self) -> None:
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

    async def connect_server(self) -> None:
        """Connect to WebSocket server."""
        server_url = config.server_url
        logger.info(f"Connecting to server: {server_url}")

        try:
            self.websocket = await connect(server_url)
            logger.info("Connected to server")
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            raise

    async def read_request_pipe(self) -> None:
        """Read from request pipe and send to WebSocket."""
        logger.info(f"Listening on request pipe: {self.request_pipe}")

        loop = asyncio.get_event_loop()
        while self.running:
            try:
                # Open pipe for reading (blocks until writer opens)
                with open(self.request_pipe, "r") as pipe:
                    while self.running:
                        line = await loop.run_in_executor(None, pipe.readline)
                        if not line:
                            break
                        line = line.strip()
                        if not line:
                            continue
                        logger.info(f"Received from pipe: {line}")

                        # Parse the command
                        # Format: "send [session] <command>"
                        parts = line.split(maxsplit=2)
                        if len(parts) < 2:
                            logger.warning(f"Invalid command format: {line}")
                            continue

                        if parts[0] == "send":
                            if len(parts) == 2:
                                session = "default"
                                command = parts[1]
                            else:
                                session = parts[1]
                                command = parts[2]

                            # Create and send task request
                            request = create_task_request(command, session)
                            if self.websocket:
                                await self.websocket.send(request.to_json())
                                logger.info(f"Sent task {request.id} to server")
                        else:
                            logger.warning(f"Unknown command: {parts[0]}")
            except FileNotFoundError:
                logger.error(f"Request pipe not found: {self.request_pipe}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error reading request pipe: {e}")
                await asyncio.sleep(1)

    async def write_response_pipe(self, response: str) -> None:
        """Write response to response pipe."""
        try:
            with open(self.response_pipe, "w") as pipe:
                pipe.write(response + "\n")
                pipe.flush()
            logger.info(f"Wrote response to pipe")
        except Exception as e:
            logger.error(f"Error writing response pipe: {e}")

    async def listen_websocket(self) -> None:
        """Listen for WebSocket messages."""
        logger.info("Listening for WebSocket messages")

        try:
            async for message in self.websocket:
                logger.info(f"Received from server: {message}")

                # Parse response
                try:
                    data = json.loads(message)
                    response = TaskResponse.from_dict(data)

                    # Write to response pipe
                    await self.write_response_pipe(message)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from server: {message}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.running = False
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.running = False

    async def run(self) -> None:
        """Main run loop."""
        self.running = True
        try:
            await self.setup()
            await self.connect_server()

            # Run both tasks concurrently
            await asyncio.gather(
                self.read_request_pipe(),
                self.listen_websocket(),
            )
        finally:
            await self.cleanup()

    async def stop(self) -> None:
        """Stop the daemon."""
        logger.info("Stopping client daemon")
        self.running = False
        if self.websocket:
            await self.websocket.close()


def main():
    """Main entry point for client daemon."""
    daemon = ClientDaemon()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        asyncio.run(daemon.stop())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")


if __name__ == "__main__":
    main()
