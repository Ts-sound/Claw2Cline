"""Configuration management for Claw2Cline."""

import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Config:
    """Claw2Cline configuration."""
    
    # WebSocket settings
    server_url: str = "ws://localhost:8765"
    server_host: str = "localhost"
    server_port: int = 8765
    
    # Cache directory
    cache_dir: Path = Path.home() / ".claw2cline"
    
    # Named pipes
    request_pipe: str = "request.pipe"
    response_pipe: str = "response.pipe"
    pid_file: str = "pid"
    
    # Cline settings
    cline_timeout: int = 3600  # 1 hour default timeout
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        cache_dir = Path(os.getenv("CLAW2CLINE_CACHE_DIR", str(Path.home() / ".claw2cline")))
        
        return cls(
            server_url=os.getenv("CLAW2CLINE_SERVER_URL", "ws://localhost:8765"),
            server_host=os.getenv("CLAW2CLINE_SERVER_HOST", "localhost"),
            server_port=int(os.getenv("CLAW2CLINE_SERVER_PORT", "8765")),
            cache_dir=cache_dir,
        )
    
    @property
    def request_pipe_path(self) -> Path:
        """Full path to request pipe."""
        return self.cache_dir / self.request_pipe
    
    @property
    def response_pipe_path(self) -> Path:
        """Full path to response pipe."""
        return self.cache_dir / self.response_pipe
    
    @property
    def pid_file_path(self) -> Path:
        """Full path to PID file."""
        return self.cache_dir / self.pid_file
    
    def ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config.from_env()