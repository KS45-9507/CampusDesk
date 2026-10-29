"""Vercel's WSGI entry point for the CampusDesk demonstration app."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web_app import application as app  # noqa: E402

