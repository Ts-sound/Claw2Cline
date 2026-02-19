import pytest
import asyncio
import json
import websockets
from websockets.server import serve
from src.server import Server, ClineTask
from src.protocol import TaskRequest, TaskStatus, MessageType

@pytest.mark.asyncio
async def test_server_connection():
    # Create server instance
    server = Server(host="localhost", port=8766)  # Use different port to avoid conflicts
    
    # Start server in background
    server_future = asyncio.create_task(server.start())
    
    try:
        # Wait a bit for server to start
        await asyncio.sleep(0.1)
        
        # Test client connection
        async with websockets.connect("ws://localhost:8766") as websocket:
            # Check if connection is established by sending/receiving a message
            # In newer versions of websockets, we can check if connection is open by attempting to send a message
            try:
                await websocket.ping()
                # Connection is open if ping succeeds
                assert True
            except:
                assert False
            
    finally:
        # Stop server gracefully
        server_future.cancel()
        try:
            await server_future
        except asyncio.CancelledError:
            pass  # Expected when cancelling the server task

@pytest.mark.asyncio
async def test_task_execution():
    # Create test server
    server = Server()
    
    # Define a simple task handler for testing
    async def test_handler(websocket, path):
        try:
            async for message in websocket:
                await server.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
    
    # Start test server
    async with serve(test_handler, "localhost", 8765):
        # Wait for server to start
        await asyncio.sleep(0.1)
        
        # Test task execution
        async with websockets.connect("ws://localhost:8765") as websocket:
            # Create test task request
            task_request = TaskRequest(command="echo 'test'")
            message = task_request.to_json()
            
            # Send task request
            await websocket.send(message)
            
            # Wait for first response (executing status)
            response = await websocket.recv()
            data = json.loads(response)
            
            # Verify initial response is executing
            assert data["type"] == MessageType.STATUS.value
            assert data["status"] == TaskStatus.EXECUTING.value
            
            # Wait for final response (success status)
            response = await websocket.recv()
            data = json.loads(response)
            
            # Verify final response
            assert data["type"] == MessageType.STATUS.value
            assert data["status"] == TaskStatus.SUCCESS.value
            assert "test" in data["output"]

@pytest.mark.asyncio
async def test_task_failure():
    # Create test server
    server = Server()
    
    # Define a simple task handler for testing
    async def test_handler(websocket, path):
        try:
            async for message in websocket:
                await server.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
    
    # Start test server
    async with serve(test_handler, "localhost", 8765):
        # Wait for server to start
        await asyncio.sleep(0.1)
        
        # Test task execution with invalid command
        async with websockets.connect("ws://localhost:8765") as websocket:
            # Create test task request with invalid command
            task_request = TaskRequest(command="invalid_command_that_does_not_exist")
            message = task_request.to_json()
            
            # Send task request
            await websocket.send(message)
            
            # Wait for first response (executing status)
            response = await websocket.recv()
            data = json.loads(response)
            
            # Verify initial response is executing
            assert data["type"] == MessageType.STATUS.value
            assert data["status"] == TaskStatus.EXECUTING.value
            
            # Wait for final response (failure status)
            response = await websocket.recv()
            data = json.loads(response)
            
            # Verify final response
            assert data["type"] == MessageType.STATUS.value
            assert data["status"] == TaskStatus.FAILED.value
            assert "not found" in data["output"] or "error" in data["output"] or "command not found" in data["output"]

@pytest.mark.asyncio
async def test_heartbeat():
    # Create test server
    server = Server()
    
    # Define a simple task handler for testing
    async def test_handler(websocket, path):
        try:
            async for message in websocket:
                await server.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
    
    # Start test server
    async with serve(test_handler, "localhost", 8765):
        # Wait for server to start
        await asyncio.sleep(0.1)
        
        # Test heartbeat
        async with websockets.connect("ws://localhost:8765") as websocket:
            # Send heartbeat
            heartbeat = {"type": "heartbeat"}
            await websocket.send(json.dumps(heartbeat))
            
            # Wait for response
            response = await websocket.recv()
            data = json.loads(response)
            
            # Verify response
            assert data["type"] == "heartbeat"
            assert data["status"] == "ok"

def test_cline_task_creation():
    # Create test task request
    task_request = TaskRequest(command="echo 'test'")
    task = ClineTask(task_request)
    
    # Verify task properties
    assert task.request == task_request
    assert task.status == TaskStatus.EXECUTING
    assert task.output == ""