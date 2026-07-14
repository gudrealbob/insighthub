"""
Add the project root to sys.path so standalone scripts can import `app`.

Usage in any script under scripts/:

    try:
        import _bootstrap  # noqa: F401
    except ModuleNotFoundError:
        import scripts._bootstrap  # noqa: F401

Then run from the repo root with either:

    python scripts/your_script.py
    python -m scripts.your_script
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
