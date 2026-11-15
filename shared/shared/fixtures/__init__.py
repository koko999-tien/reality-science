"""Fixtures namespace package for shared."""
import sys
from pathlib import Path

# Add shared/fixtures to module path if needed
_parent_fixtures = Path(__file__).resolve().parent.parent.parent / "fixtures"
if str(_parent_fixtures) not in sys.path:
    sys.path.insert(0, str(_parent_fixtures.parent))
