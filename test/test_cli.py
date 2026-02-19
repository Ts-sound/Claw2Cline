import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.cli import send_command, status_command, main

class TestCLI:
    @patch('src.cli.config')
    def test_send_command_success(self, mock_config):
        # Mock config values
        mock_cache_dir = Path("/tmp/claw2cline-test")
        mock_config.cache_dir = mock_cache_dir
        mock_config.request_pipe_path = mock_cache_dir / "request.pipe"
        mock_config.response_pipe_path = mock_cache_dir / "response.pipe"
        
        # Create test pipe
        try:
            os.mkfifo(str(mock_config.request_pipe_path))
            os.mkfifo(str(mock_config.response_pipe_path))
        except FileExistsError:
            pass  # Pipes may already exist
            
        # Mock arguments
        args = type('Args', (), {
            'command': 'echo "test"',
            'session': 'default',
            'wait': False
        })()
            
        # Run send command
        result = send_command(args)
        assert result == 0
        
    @patch('src.cli.config')
    def test_send_command_with_wait(self, mock_config):
        # Mock config values
        mock_cache_dir = Path("/tmp/claw2cline-test")
        mock_config.cache_dir = mock_cache_dir
        mock_config.request_pipe_path = mock_cache_dir / "request.pipe"
        mock_config.response_pipe_path = mock_cache_dir / "response.pipe"
        
        # Create test pipe
        try:
            os.mkfifo(str(mock_config.request_pipe_path))
            os.mkfifo(str(mock_config.response_pipe_path))
        except FileExistsError:
            pass
            
        # Mock arguments
        args = type('Args', (), {
            'command': 'echo "test"',
            'session': 'default',
            'wait': True
        })()
            
        # Run send command
        result = send_command(args)
        assert result == 0
    
    @patch('src.cli.config')
    def test_send_command_no_pipe(self, mock_config):
        # Mock config values
        mock_cache_dir = Path("/tmp/claw2cline-test")
        mock_config.cache_dir = mock_cache_dir
        mock_config.request_pipe_path = mock_cache_dir / "request.pipe"
        mock_config.response_pipe_path = mock_cache_dir / "response.pipe"
        
        # Ensure pipes don't exist
        if mock_config.request_pipe_path.exists():
            os.remove(str(mock_config.request_pipe_path))
        if mock_config.response_pipe_path.exists():
            os.remove(str(mock_config.response_pipe_path))
            
        # Mock arguments
        args = type('Args', (), {
            'command': 'echo "test"',
            'session': 'default',
            'wait': False
        })()
            
        # Run send command
        result = send_command(args)
        assert result == 1
    
    @patch('src.cli.config')
    def test_status_command(self, mock_config):
        # Mock config values
        mock_cache_dir = Path("/tmp/claw2cline-test")
        mock_config.cache_dir = mock_cache_dir
        mock_config.pid_file_path = mock_cache_dir / "pid"
        
        # Run status command
        result = status_command(type('Args', (), {})())
        assert result == 0
    
    @patch('sys.stdout')
    def test_main_no_command(self, mock_stdout):
        # Test main with no command
        with patch.object(sys, 'argv', ['claw2cline']):
            result = main()
            assert result == 1
    
    @patch('src.cli.status_command')
    def test_main_status_command(self, mock_status):
        # Test main with status command
        with patch.object(sys, 'argv', ['claw2cline', 'status']):
            result = main()
            assert result == 0
            mock_status.assert_called_once()