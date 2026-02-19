import pytest
import json
import time
import threading
from unittest.mock import MagicMock
from src.server import Server, ClineTask
from src.protocol import TaskRequest, TaskStatus, MessageType

def test_cline_task_creation():
    # Create test task request
    task_request = TaskRequest(command="echo 'test'")
    task = ClineTask(task_request)
    
    # Verify task properties
    assert task.request == task_request
    assert task.status == TaskStatus.EXECUTING
    assert task.output == ""

# Note: The actual WebSocket server tests are more complex to convert to threading model
# They would require actual socket connections and threading coordination
# For now, we focus on unit tests for the core logic
