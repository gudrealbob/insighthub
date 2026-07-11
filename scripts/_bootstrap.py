"""
Add the project root to sys.path so standalone scripts can import `app`.

Usage in any script under scripts/:

    import _bootstrap  # noqa: F401

Place this import before any `from app...` imports, then run from the repo root:

    python scripts/your_script.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
