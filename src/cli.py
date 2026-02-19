"""Command line interface for Claw2Cline."""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from .config import config
from .protocol import TaskResponse, TaskStatus

# Timeout for waiting for responses (in seconds)
DEFAULT_RESPONSE_TIMEOUT = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_command(args) -> int:
    """Send a command through the request pipe."""
    request_pipe = config.request_pipe_path
    response_pipe = config.response_pipe_path

    # Check if pipes exist
    if not request_pipe.exists():
        logger.error(f"Request pipe not found: {request_pipe}")
        logger.error("Is clientd running?")
        return 1

    # Build command
    message = f"send"
    if args.session:
        message += f" {args.session}"
    message += f" {args.command}"

    try:
        # Write to request pipe
        logger.info(f"Writing command to request pipe: {request_pipe}")
        with open(request_pipe, "w") as pipe:
            pipe.write(message + "\n")
            pipe.flush()
        logger.info(f"Sent command: {message}")
    except Exception as e:
        logger.error(f"Failed to write to request pipe: {e}")
        return 1

    # If --wait flag is set, wait for response
    if args.wait:
        logger.info("Waiting for task completion...")
        
        # Clear any old responses in the pipe
        try:
            with open(response_pipe, "r") as pipe:
                # Try to read any existing content to clear the pipe
                try:
                    pipe.read()
                except:
                    pass
        except:
            pass  # Ignore if pipe is empty or doesn't exist yet

        # Wait for response with timeout
        start_time = time.time()
        while time.time() - start_time < DEFAULT_RESPONSE_TIMEOUT:
            try:
                with open(response_pipe, "r") as pipe:
                    response_data = pipe.read()
                    if response_data:
                        # Parse the response
                        import json
                        try:
                            response_json = json.loads(response_data.strip().split('\n')[0])
                            status = response_json.get('status', '')
                            output = response_json.get('output', '')
                            
                            if status in ['success', 'failed']:
                                print(f"Task completed with status: {status}")
                                if output:
                                    print(f"Output: {output}")
                                return 0 if status == 'success' else 1
                        except json.JSONDecodeError:
                            pass  # Continue waiting if JSON is malformed
            except FileNotFoundError:
                pass  # Continue waiting if pipe doesn't exist yet
            except Exception as e:
                logger.warning(f"Error reading response pipe: {e}")
            
            time.sleep(0.1)  # Short sleep to prevent busy waiting
        
        logger.warning("Timeout waiting for response")
        return 1

    return 0


def status_command(args) -> int:
    """Show status of Claw2Cline."""
    pid_file = config.pid_file_path
    cache_dir = config.cache_dir

    print(f"Cache directory: {cache_dir}")
    print(f"Request pipe: {config.request_pipe_path}")
    print(f"Response pipe: {config.response_pipe_path}")
    print(f"PID file: {pid_file}")

    # Check if clientd is running
    if pid_file.exists():
        with open(pid_file, "r") as f:
            pid = f.read().strip()
        print(f"Clientd PID: {pid}")
        # Check if process is running
        try:
            import os

            os.kill(int(pid), 0)
            print("Clientd status: running")
        except (OSError, ValueError):
            print("Clientd status: not running (stale PID file)")
    else:
        print("Clientd status: not running")

    return 0


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog="claw2cline",
        description="Claw2Cline - WebSocket Bridge for OpenClaw to Cline",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # send command
    send_parser = subparsers.add_parser("send", help="Send a task to Cline")
    send_parser.add_argument("command", help="Task command to send")
    send_parser.add_argument("--session", "-s", default=None, help="Session name (default: default)")
    send_parser.add_argument("--wait", "-w", action="store_true", help="Wait for task completion")
    send_parser.set_defaults(func=send_command)

    # status command
    status_parser = subparsers.add_parser("status", help="Show Claw2Cline status")
    status_parser.set_defaults(func=status_command)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
