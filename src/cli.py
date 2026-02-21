"""Command line interface for Claw2Cline."""

import argparse
import json
import logging
import sys
import time
import os
import glob
from pathlib import Path
from .config import config
from .protocol import TaskResponse, TaskStatus

# Timeout for waiting for responses (in seconds)
DEFAULT_RESPONSE_TIMEOUT = 5

# Default workspace directory
WORKSPACE_DIR = "/opt/tong/ws/git-repo"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def list_projects(workspace_dir=WORKSPACE_DIR):
    """List all projects in the workspace directory."""
    if not os.path.exists(workspace_dir):
        logger.error(f"Workspace directory does not exist: {workspace_dir}")
        return []

    projects = []
    for item in os.listdir(workspace_dir):
        item_path = os.path.join(workspace_dir, item)
        if os.path.isdir(item_path):
            # Check if it looks like a project directory (has common project files)
            project_indicators = [".git", "README.md", "package.json", "setup.py", "requirements.txt", "pyproject.toml"]
            if any(os.path.exists(os.path.join(item_path, indicator)) for indicator in project_indicators):
                projects.append(item)

    return sorted(projects)


def workspace_command(args) -> int:
    """Show workspace information by querying the server."""
    request_pipe = config.request_pipe_path
    response_pipe = config.response_pipe_path

    # Check if pipes exist
    if not request_pipe.exists():
        logger.error(f"Request pipe not found: {request_pipe}")
        logger.error("Is clientd running?")
        return 1

    try:
        # Send workspace query to pipe
        logger.info(f"Writing workspace query to request pipe: {request_pipe}")
        with open(request_pipe, "w") as pipe:
            pipe.write("workspace\n")
            pipe.flush()
        logger.info("Sent workspace query")
    except Exception as e:
        logger.error(f"Failed to write to request pipe: {e}")
        return 1

    # Wait for response with timeout
    start_time = time.time()
    while time.time() - start_time < DEFAULT_RESPONSE_TIMEOUT:
        try:
            with open(response_pipe, "r") as pipe:
                response_data = pipe.read()
                if response_data:
                    # Parse the response
                    try:
                        response_json = json.loads(response_data.strip().split("\n")[0])
                        msg_type = response_json.get("type", "")

                        if msg_type == "workspace_status":
                            workspace_dir = response_json.get("workspace_dir", "Unknown")
                            exists = response_json.get("exists", False)
                            projects_count = response_json.get("projects_count", 0)

                            print(f"Workspace directory: {workspace_dir}")
                            if exists:
                                print(f"Status: Available")
                                print(f"Projects found: {projects_count}")
                            else:
                                print(f"Status: Not found - {workspace_dir} does not exist")
                            return 0
                        else:
                            logger.warning(f"Unexpected response type: {msg_type}")
                    except json.JSONDecodeError:
                        pass  # Continue waiting if JSON is malformed
        except FileNotFoundError:
            pass  # Continue waiting if pipe doesn't exist yet
        except Exception as e:
            logger.warning(f"Error reading response pipe: {e}")

        time.sleep(0.1)  # Short sleep to prevent busy waiting

    logger.warning("Timeout waiting for workspace response")
    return 1


def projects_command(args) -> int:
    """List projects in the workspace by querying the server."""
    request_pipe = config.request_pipe_path
    response_pipe = config.response_pipe_path

    # Check if pipes exist
    if not request_pipe.exists():
        logger.error(f"Request pipe not found: {request_pipe}")
        logger.error("Is clientd running?")
        return 1

    try:
        # Send projects query to pipe
        logger.info(f"Writing projects query to request pipe: {request_pipe}")
        with open(request_pipe, "w") as pipe:
            pipe.write("projects\n")
            pipe.flush()
        logger.info("Sent projects query")
    except Exception as e:
        logger.error(f"Failed to write to request pipe: {e}")
        return 1

    # Wait for response with timeout
    start_time = time.time()
    while time.time() - start_time < DEFAULT_RESPONSE_TIMEOUT:
        try:
            with open(response_pipe, "r") as pipe:
                response_data = pipe.read()
                if response_data:
                    # Parse the response
                    try:
                        response_json = json.loads(response_data.strip().split("\n")[0])
                        msg_type = response_json.get("type", "")

                        if msg_type == "projects_list":
                            workspace_dir = response_json.get("workspace_dir", "Unknown")
                            projects = response_json.get("projects", [])
                            count = response_json.get("count", len(projects))

                            if projects:
                                print(f"Found {count} projects in workspace ({workspace_dir}):")
                                for project in projects:
                                    print(f"  - {project}")
                            else:
                                print(f"No projects found in workspace ({workspace_dir})")
                            return 0
                        else:
                            logger.warning(f"Unexpected response type: {msg_type}")
                    except json.JSONDecodeError:
                        pass  # Continue waiting if JSON is malformed
        except FileNotFoundError:
            pass  # Continue waiting if pipe doesn't exist yet
        except Exception as e:
            logger.warning(f"Error reading response pipe: {e}")

        time.sleep(0.1)  # Short sleep to prevent busy waiting

    logger.warning("Timeout waiting for projects response")
    return 1


def send_command(args) -> int:
    """Send a command through the request pipe."""
    request_pipe = config.request_pipe_path
    response_pipe = config.response_pipe_path

    # Check if pipes exist
    if not request_pipe.exists():
        logger.error(f"Request pipe not found: {request_pipe}")
        logger.error("Is clientd running?")
        return 1

    # Build command - if project is specified, pass project name to be resolved by server
    # The server side will handle project path resolution and validation
    if hasattr(args, "project") and args.project:
        # Pass project name to server for resolution
        # Server will construct: cline -y -c "/path/to/project" "command"
        message = f"send {args.session or 'default'} --project {args.project} {args.command}"
    else:
        # Regular command without project specification
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

    # Wait for task completion (synchronous mode)
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
    while time.time() - start_time < DEFAULT_RESPONSE_TIMEOUT * 12:  # Extended timeout for long tasks
        try:
            with open(response_pipe, "r") as pipe:
                response_data = pipe.read()
                if response_data:
                    # Parse the response
                    try:
                        response_json = json.loads(response_data.strip().split("\n")[0])
                        status = response_json.get("status", "")
                        output = response_json.get("output", "")

                        if status in ["success", "failed"]:
                            print(f"Task completed with status: {status}")
                            if output:
                                print(f"Output: {output}")
                            return 0 if status == "success" else 1
                    except json.JSONDecodeError:
                        pass  # Continue waiting if JSON is malformed
        except FileNotFoundError:
            pass  # Continue waiting if pipe doesn't exist yet
        except Exception as e:
            logger.warning(f"Error reading response pipe: {e}")

        time.sleep(0.1)  # Short sleep to prevent busy waiting

    logger.warning("Timeout waiting for response")
    return 1


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
    send_parser.add_argument("--project", "-p", help="Project name to execute command in")
    send_parser.set_defaults(func=send_command)

    # status command
    status_parser = subparsers.add_parser("status", help="Show Claw2Cline status")
    status_parser.set_defaults(func=status_command)

    # workspace command
    workspace_parser = subparsers.add_parser("workspace", help="Manage workspace and projects")
    workspace_subparsers = workspace_parser.add_subparsers(dest="subcommand", help="Workspace subcommands")

    # workspace status
    workspace_status_parser = workspace_subparsers.add_parser("status", help="Show workspace status")
    workspace_status_parser.set_defaults(func=workspace_command)

    # workspace default (status)
    workspace_parser.set_defaults(func=workspace_command, subcommand="status")

    # projects command
    projects_parser = subparsers.add_parser("projects", help="List projects in workspace")
    projects_parser.set_defaults(func=projects_command)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 1

    # Handle the case where func is not set for workspace without subcommand
    if args.command == "workspace" and not hasattr(args, "func"):
        args.func = workspace_command

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
