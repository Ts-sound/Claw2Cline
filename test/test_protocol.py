import pytest
from src.protocol import Message, MessageType, TaskRequest, TaskStatus, TaskResponse

def test_message_creation():
    msg = Message()
    assert msg.type == MessageType.TASK
    assert isinstance(msg.id, str)
    assert isinstance(msg.timestamp, int)

def test_message_to_dict():
    msg = Message(id="123", type=MessageType.STATUS, timestamp=123456)
    result = msg.to_dict()
    assert result["id"] == "123"
    assert result["type"] == "status"
    assert result["timestamp"] == 123456

def test_message_from_dict():
    data = {"id": "123", "type": "heartbeat", "timestamp": 123456}
    msg = Message.from_dict(data)
    assert msg.id == "123"
    assert msg.type == MessageType.HEARTBEAT
    assert msg.timestamp == 123456

def test_task_request():
    req = TaskRequest(command="test", session="default")
    assert req.type == MessageType.TASK
    assert req.command == "test"
    assert req.session == "default"

def test_task_response():
    resp = TaskResponse(status=TaskStatus.SUCCESS, output="result")
    assert resp.type == MessageType.STATUS
    assert resp.status == TaskStatus.SUCCESS
    assert resp.output == "result"

def test_create_task_request():
    req = req = TaskRequest(command="test", session="default")
    assert req.command == "test"
    assert req.session == "default"

def test_create_task_response():
    resp = TaskResponse(id="123", status=TaskStatus.FAILED, output="error")
    assert resp.id == "123"
    assert resp.status == TaskStatus.FAILED
    assert resp.output == "error"