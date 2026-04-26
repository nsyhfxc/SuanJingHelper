from __future__ import annotations

from pathlib import Path

APP_NAME = "算法竞赛调试助手"
APP_VERSION = "1.1"

APP_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = APP_ROOT / "data"
WORKSPACE_DIR = APP_ROOT / "workspace"
EXAMPLES_DIR = APP_ROOT / "examples"

TEMPLATE_PATH = DATA_DIR / "templates.json"
LEGACY_TEMPLATE_PATH = APP_ROOT / "my_templates.json"


def ensure_app_dirs() -> None:
    """Create runtime directories used by the app."""
    DATA_DIR.mkdir(exist_ok=True)
    WORKSPACE_DIR.mkdir(exist_ok=True)
    EXAMPLES_DIR.mkdir(exist_ok=True)


PALETTE = {
    "background": "#0f172a",
    "sidebar": "#111827",
    "surface": "#182235",
    "surface_alt": "#223047",
    "border": "#334155",
    "muted": "#94a3b8",
    "text": "#e5e7eb",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "success": "#16a34a",
    "success_hover": "#15803d",
    "danger": "#dc2626",
    "danger_hover": "#b91c1c",
    "warning": "#f59e0b",
}
