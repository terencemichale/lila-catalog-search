"""Portable demo paths; the original business catalog is never required."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
CATALOG_ROOT = REPO_ROOT / "data" / "catalog"

def repo_root() -> Path:
    return REPO_ROOT

def catalog_root() -> Path:
    return CATALOG_ROOT
