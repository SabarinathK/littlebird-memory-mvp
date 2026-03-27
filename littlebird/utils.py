import sys
from datetime import datetime, timezone

from .config import log


def require(package, install_name=None):
    import importlib

    try:
        return importlib.import_module(package)
    except ImportError:
        name = install_name or package
        log.error(f"Missing package '{name}'. Run: pip install {name}")
        sys.exit(1)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_extraction_result() -> dict:
    return {
        "entities": [],
        "relationships": [],
        "summary": "",
        "is_sensitive": False,
    }
