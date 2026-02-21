"""Message protocol definitions for Claw2Cline."""
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json

class MessageType(str, Enum):
    """Message types."""
    TASK = "task"
    STATUS = "status"
    HEARTBEAT = "heartbeat"
    GET_TASK_STATUS = "get_task_status"
    WORKSPACE_QUERY = "workspace_query"
    PROJECTS_QUERY = "projects_query"

class TaskStatus(str, Enum):
    """Task status values."""
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class Message:
    """Base message structure."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TASK
    timestamp: int = field(default_factory=lambda: int(time.time()))
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return { 
            "id": self.id, 
            "type": self.type.value, 
            "timestamp": self.timestamp, 
        }
        
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
        
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=MessageType(data.get("type", "task")),
            timestamp=data.get("timestamp", int(time.time())),
        )
        
    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

@dataclass
class TaskRequest(Message):
    """Task request message."""
    session: str = "default"
    command: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = super().to_dict()
        data.update({ 
            "session": self.session, 
            "command": self.command, 
        })
        return data
        
    @classmethod
    def from_dict(cls, data: dict) -> "TaskRequest":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=MessageType(data.get("type", "task")),
            timestamp=data.get("timestamp", int(time.time())),
            session=data.get("session", "default"),
            command=data.get("command", ""),
        )

@dataclass
class TaskResponse(Message):
    """Task response message."""
    status: TaskStatus = TaskStatus.EXECUTING
    output: str = ""
    
    def __post_init__(self):
        """Set the message type to STATUS after initialization."""
        self.type = MessageType.STATUS
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = super().to_dict()
        data.update({ 
            "status": self.status.value, 
            "output": self.output, 
        })
        return data
        
    @classmethod
    def from_dict(cls, data: dict) -> "TaskResponse":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=MessageType(data.get("type", "status")),
            timestamp=data.get("timestamp", int(time.time())),
            status=TaskStatus(data.get("status", "executing")),
            output=data.get("output", ""),
        )

def create_task_request(command: str, session: str = "default") -> TaskRequest:
    """Create a new task request."""
    return TaskRequest(
        command=command,
        session=session,
    )

def create_task_response( request_id: str, status: TaskStatus, output: str = "" ) -> TaskResponse:
    """Create a task response."""
    return TaskResponse(
        id=request_id,
        status=status,
        output=output,
    )