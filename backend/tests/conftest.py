"""
Pytest configuration and fixtures for checkpoint tests.
"""
import sys
import os

# Add the backend directory to the path so imports work
backend_dir = os.path.dirname(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
