"""Helpers for locating files in source and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path


def _get_bundle_root() -> Path:
    """Return the directory where bundled resources are extracted."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _get_app_root() -> Path:
    """Return the directory where the app should read user-provided files."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BUNDLE_ROOT = _get_bundle_root()
APP_ROOT = _get_app_root()
ASSETS_DIR = BUNDLE_ROOT / "assets"
PROMPT_FILE = BUNDLE_ROOT / "prompt.txt"
