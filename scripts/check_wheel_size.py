#!/usr/bin/env python3

import os
import sys
from pathlib import Path


def check_wheel_size(max_size_mb=8):
    """Check if wheel size is within the specified limit.
    
    Args:
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        True if wheel size is within limit, False otherwise
    """
    # Find wheel file in dist directory
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("Error: dist directory not found. Run 'python -m build --wheel' first.")
        return False
    
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        print("Error: No wheel files found in dist directory.")
        return False
    
    # Get the most recent wheel file
    wheel_file = max(wheel_files, key=os.path.getmtime)
    
    # Check size
    size_bytes = os.path.getsize(wheel_file)
    size_mb = size_bytes / (1024 * 1024)  # Convert to MB
    
    print(f"Wheel file: {wheel_file.name}")
    print(f"Size: {size_mb:.2f} MB")
    
    if size_mb >= max_size_mb:
        print(f"Error: Wheel size exceeds {max_size_mb} MB limit")
        return False
    else:
        print(f"Success: Wheel size is within {max_size_mb} MB limit")
        return True


if __name__ == "__main__":
    # Allow custom max size via command line argument
    max_size = 8  # Default
    if len(sys.argv) > 1:
        try:
            max_size = float(sys.argv[1])
        except ValueError:
            print(f"Error: Invalid max size '{sys.argv[1]}'. Using default {max_size} MB.")
    
    result = check_wheel_size(max_size)
    sys.exit(0 if result else 1)
