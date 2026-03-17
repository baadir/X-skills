"""
conftest.py — Test configuration for The Creator test suite.

Adds the-creator/ directory to sys.path so tests can import
Creator modules directly without package prefix.
"""
import sys
from pathlib import Path

# Add the-creator/ to sys.path so direct imports work
_SKILL_DIR = Path(__file__).parent.parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))
