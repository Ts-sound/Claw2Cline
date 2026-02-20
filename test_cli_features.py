#!/usr/bin/env python3
"""Test script to verify CLI features for workspace and project support."""

import subprocess
import sys
import os

def run_command(cmd):
    """Run a command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")
    print("-" * 50)
    return result

def main():
    print("Testing CLI features for workspace and project support\n")
    
    # Test 1: Help command
    run_command("python3 -m src.cli --help")
    
    # Test 2: Workspace command
    run_command("python3 -m src.cli workspace")
    
    # Test 3: Projects command
    run_command("python3 -m src.cli projects")
    
    # Test 4: Send command help (to verify --project option exists)
    run_command("python3 -m src.cli send --help")
    
    # Test 5: Status command
    run_command("python3 -m src.cli status")
    
    print("All tests completed!")

if __name__ == "__main__":
    main()