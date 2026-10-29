"""Vercel's WSGI entry point for the CampusDesk demonstration app."""

from pathlib import Path
import sys
from urllib.parse import parse_qsl, urlencode

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web_app import application as _application  # noqa: E402


def app(environ, start_response):
    """Restore the visitor's route after Vercel's catch-all function rewrite."""
    query = parse_qsl(environ.get("QUERY_STRING", ""), keep_blank_values=True)
    routed_path = next((value for key, value in query if key == "__campusdesk_path"), None)
    if routed_path is not None:
        environ["PATH_INFO"] = routed_path
        environ["QUERY_STRING"] = urlencode(
            [(key, value) for key, value in query if key != "__campusdesk_path"]
        )
    return _application(environ, start_response)

