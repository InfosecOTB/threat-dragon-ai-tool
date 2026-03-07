"""Helpers for locating files in source and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path


def _get_bundle_root() -> Path:
    """Return the directory where bundled resources are extracted."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent

def _get_config_root() -> Path:
    """Return the directory where user config should be stored."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent.parent

    executable_path = Path(sys.executable).resolve()

    # For app bundles (MyApp.app/Contents/MacOS/<binary>), keep config outside
    # the bundle so the app can update it and users can find it easily.
    if sys.platform == "darwin":
        for parent in executable_path.parents:
            if parent.suffix.lower() == ".app":
                return parent.parent

    return executable_path.parent


BUNDLE_ROOT = _get_bundle_root()
CONFIG_ROOT = _get_config_root()
ASSETS_DIR = BUNDLE_ROOT / "assets"
PROMPT_FILE = BUNDLE_ROOT / "prompt.txt"
CONFIG_FILE = CONFIG_ROOT / "config.json"
