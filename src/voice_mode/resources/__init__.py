"""Auto-import all tools for registration with FastMCP."""
import os
import importlib
from pathlib import Path

# Get the directory containing this file
tools_dir = Path(__file__).parent

# Import all Python files in this directory (except __init__.py)
for file in tools_dir.glob("*.py"):
    if file.name != "__init__.py" and not file.name.startswith("_"):
        module_name = file.stem
        importlib.import_module(f".{module_name}", package=__name__)