import pytest
import sys
import os
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.config import config
from src.cli import send_command, status_command, main
from src.clientd import ClientDaemon


class TestCLI:

    def setup_method(self):
        """Setup method to open pipes for reading data."""
        print("Setting up pipes for reading data...")
        # Create cache directory
        config.ensure_cache_dir()

        # Create named pipes
        os.makedirs(config.cache_dir, exist_ok=True)
        try:
            if not config.request_pipe_path.exists():
                os.mkfifo(str(config.request_pipe_path))
            if not config.response_pipe_path.exists():
                os.mkfifo(str(config.response_pipe_path))
        except FileExistsError:
            pass  # Pipes may already exist
        except Exception as e:
            print(f"Error creating pipes: {e}")
            raise

        # thread to read from request pipe

        def read_request_pipe():
            with open(config.request_pipe_path, "r") as pipe:
                print("Pipes are set up and ready for testing.")
                data = pipe.read()  # Block until data is written to the pipe
                print(f"Received data from request pipe: {data}")

        self.thread = threading.Thread(target=read_request_pipe)
        self.thread.start()

    def teardown_method(self):
        """Teardown method to close pipes after each test."""
        print("Tearing down pipes...")
        try:
            # Clean up pipes
            if config.request_pipe_path.exists():
                config.request_pipe_path.unlink()
            if config.response_pipe_path.exists():
                config.response_pipe_path.unlink()
            print("Pipes cleaned up successfully")
        except Exception as e:
            print(f"Error cleaning up pipes: {e}")

    def test_send_command_success(self):
        print("Testing send_command without wait")
        # Mock arguments
        args = type("Args", (), {"command": 'echo "test"', "session": "default", "wait": False})()

        # Run send command
        print("Testing send_command with args:", args)
        result = send_command(args)
        self.thread.join(timeout=5)  # Wait for the thread to finish reading from the pipe
        assert result == 0
