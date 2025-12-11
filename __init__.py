"""session_manager manager module."""

# Add path handling to work from the new nested directory structure
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.getcwd()  # Use current working directory as project root
sys.path.insert(0, project_root)

from managers.session_manager.session_manager import SessionManager
from managers.session_manager.models import Base, User, Session
from managers.session_manager.session_manager_cli import register_cli

__all__ = ["SessionManager", "Base", "User", "Session", "register_cli"]
