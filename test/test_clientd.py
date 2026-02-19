import pytest
import json
import time
import tempfile
import os
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.clientd import ClientDaemon
from src.protocol import MessageType, TaskStatus, TaskRequest, TaskResponse, create_task_request


class TestClientDaemon:
    """Test cases for ClientDaemon polling mechanism."""
    
    def setup_method(self):
        """Setup method to create a temporary cache directory for testing."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cache_dir = None
        
        # Store original config
        from src.config import config as global_config
        self.original_cache_dir = global_config.cache_dir
        self.original_request_pipe = global_config.request_pipe
        self.original_response_pipe = global_config.response_pipe
        self.original_pid_file = global_config.pid_file
        
        # Temporarily change the global config
        global_config.cache_dir = self.temp_dir
        global_config.request_pipe = "request.pipe"
        global_config.response_pipe = "response.pipe"
        global_config.pid_file = "pid"
        
    def teardown_method(self):
        """Teardown method to clean up temporary files."""
        from src.config import config as global_config
        # Restore original config
        global_config.cache_dir = self.original_cache_dir
        global_config.request_pipe = self.original_request_pipe
        global_config.response_pipe = self.original_response_pipe
        global_config.pid_file = self.original_pid_file
        
        # Clean up temporary files
        for file_path in self.temp_dir.glob("*"):
            if file_path.exists():
                file_path.unlink()
        if self.temp_dir.exists():
            self.temp_dir.rmdir()
    
    def test_initialization(self):
        """Test ClientDaemon initialization."""
        daemon = ClientDaemon()
        
        assert daemon.request_pipe == self.temp_dir / "request.pipe"
        assert daemon.response_pipe == self.temp_dir / "response.pipe"
        assert daemon.pid_file == self.temp_dir / "pid"
        assert daemon.active_tasks == {}
        
    def test_start_task_polling(self):
        """Test starting task polling."""
        daemon = ClientDaemon()
        daemon.running = True
        
        # Mock the websocket
        daemon.websocket = MagicMock()
        
        # Start polling for a task
        task_id = "test-task-123"
        daemon.start_task_polling(task_id)
        
        # Check that the task is in active tasks
        assert task_id in daemon.active_tasks
        assert daemon.active_tasks[task_id] is True
        
        # Stop polling to avoid async task running during test
        if task_id in daemon.active_tasks:
            del daemon.active_tasks[task_id]
    
    def test_send_status_query(self):
        """Test sending status query."""
        daemon = ClientDaemon()
        
        # Mock the websocket
        daemon.websocket = MagicMock()
        daemon.websocket.send = MagicMock()
        
        task_id = "test-task-456"
        daemon.send_status_query(task_id)
        
        # Verify that send was called with the correct status query
        assert daemon.websocket.send.called
        call_args = daemon.websocket.send.call_args[0][0]
        sent_data = json.loads(call_args)
        
        assert sent_data["type"] == MessageType.GET_TASK_STATUS.value
        assert sent_data["task_id"] == task_id
        assert "timestamp" in sent_data
    
    def test_listen_websocket_handles_status_response(self):
        """Test that listen_websocket handles status responses correctly."""
        daemon = ClientDaemon()
        daemon.running = True  # Keep running to process the message
        daemon.active_tasks = {"completed-task": True}
        
        # Create a mock websocket that returns a status response once, then stops
        class MockWebSocket:
            def __init__(self):
                self.first_call = True
            
            def recv(self):
                if self.first_call:
                    self.first_call = False
                    # Send a completed task response
                    response = TaskResponse(
                        id="completed-task",
                        status=TaskStatus.SUCCESS,
                        output="Task completed successfully"
                    ).to_json()
                    return response
                else:
                    # Stop the loop by raising an exception
                    raise Exception("Stop reading")
        
        daemon.websocket = MockWebSocket()
        
        # Mock the write_response_pipe method to avoid file operations
        daemon.write_response_pipe = MagicMock()
        
        # Call listen_websocket - this will process the response
        try:
            daemon.listen_websocket()
        except Exception:
            pass  # Expected to stop when MockWebSocket.recv raises exception
        
        # Verify that the completed task was removed from active tasks
        assert "completed-task" not in daemon.active_tasks


def test_clientd_integration():
    """Integration test for ClientDaemon polling workflow."""
    daemon = ClientDaemon()
    daemon.running = True
    
    # Mock the websocket
    daemon.websocket = MagicMock()
    daemon.websocket.send = MagicMock()
    
    # Simulate receiving a task request through the pipe
    task_request = create_task_request("echo 'test'", "default")
    
    # Manually trigger the polling mechanism
    daemon.start_task_polling(task_request.id)
    
    # Verify task is being polled
    assert task_request.id in daemon.active_tasks
    
    # Send a status query
    daemon.send_status_query(task_request.id)
    
    # Verify the query was sent
    assert daemon.websocket.send.called
    
    # Clean up
    if task_request.id in daemon.active_tasks:
        del daemon.active_tasks[task_request.id]
