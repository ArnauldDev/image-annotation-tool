#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

_src_dir = Path(__file__).resolve().parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from iat.main import main as launch_editor  # noqa: E402


if __name__ == "__main__":
    launch_editor()
