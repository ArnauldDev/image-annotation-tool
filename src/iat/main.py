#!/usr/bin/env python3
# File Name: main.py
# Description: Application entry point for the Image Annotation Tool
# Developer: ArnauldDev
# Created Date: 2026-09-21
# Last Modified: 2026-09-21

"""Entry point module, used by `python -m iat` and the root main.py launcher."""

import sys
from pathlib import Path

_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from iat.qt_image_editor import main

__all__ = ["main"]

if __name__ == "__main__":
    main()
