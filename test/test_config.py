import os
import pytest
from pathlib import Path
from src.config import Config, config

def test_default_config():
    assert config.server_url == "ws://localhost:8765"
    assert config.server_host == "localhost"
    assert config.server_port == 8765
    assert config.cache_dir == Path.home() / ".claw2cline"

def test_config_from_env():
    # Set environment variables
    os.environ["CLAW2CLINE_SERVER_URL"] = "ws://test:8080"
    os.environ["CLAW2CLINE_SERVER_HOST"] = "testhost"
    os.environ["CLAW2CLINE_SERVER_PORT"] = "9090"
    os.environ["CLAW2CLINE_CACHE_DIR"] = "/tmp/claw2cline"
    
    try:
        # Create config from environment
        test_config = Config.from_env()
        
        # Verify environment variables are respected
        assert test_config.server_url == "ws://test:8080"
        assert test_config.server_host == "testhost"
        assert test_config.server_port == 9090
        assert test_config.cache_dir == Path("/tmp/claw2cline")
    finally:
        # Clean up environment variables
        del os.environ["CLAW2CLINE_SERVER_URL"]
        del os.environ["CLAW2CLINE_SERVER_HOST"]
        del os.environ["CLAW2CLINE_SERVER_PORT"]
        del os.environ["CLAW2CLINE_CACHE_DIR"]

def test_config_property_paths():
    assert config.request_pipe_path == config.cache_dir / "request.pipe"
    assert config.response_pipe_path == config.cache_dir / "response.pipe"
    assert config.pid_file_path == config.cache_dir / "pid"

def test_ensure_cache_dir():
    test_dir = Path("/tmp/claw2cline-test")
    
    try:
        test_config = Config(cache_dir=test_dir)
        test_config.ensure_cache_dir()
        assert test_dir.exists()
    finally:
        # Clean up - remove directory and all contents
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
