import uuid
from typing import Optional

from .config import CONFIG, log
from .utils import require, utc_now_iso


class ScreenCapture:
    """
    Reads text from the active foreground window using
    Windows UI Automation API via pywinauto.
    Falls back to win32gui window title if UIA fails.
    """

    def __init__(self):
        self.win32gui = require("win32gui", "pywin32")
        self.win32process = require("win32process", "pywin32")
        self.psutil = require("psutil")
        self.desktop = None
        self.uia_available = False
        self._init_uia()

    def _init_uia(self):
        try:
            from pywinauto import Desktop

            self.desktop = Desktop(backend="uia")
            self.uia_available = True
            log.info("UI Automation (pywinauto) available")
        except Exception:
            self.uia_available = False
            log.warning("pywinauto not available - falling back to window title only")

    def get_active_app_info(self) -> dict:
        import psutil
        import win32gui
        import win32process

        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            return {
                "app": proc.name(),
                "title": win32gui.GetWindowText(hwnd),
                "pid": pid,
            }
        except Exception:
            return {"app": "unknown", "title": "", "pid": 0}

    def is_ignored(self, app_info: dict) -> bool:
        app = app_info.get("app", "").lower()
        title = app_info.get("title", "").lower()

        for ignored in CONFIG["ignored_apps"]:
            if ignored.lower() in app:
                return True

        for keyword in CONFIG["ignored_titles"]:
            if keyword in title:
                return True

        return False

    def capture(self) -> Optional[dict]:
        app_info = self.get_active_app_info()
        if self.is_ignored(app_info):
            return None

        text = self._capture_text(app_info)
        if not text.strip():
            return None

        return {
            "id": str(uuid.uuid4()),
            "type": "screen",
            "source_app": app_info["app"],
            "window_title": app_info["title"],
            "content": text[:4000],
            "timestamp": utc_now_iso(),
        }

    def _capture_text(self, app_info: dict) -> str:
        text = ""

        if self.uia_available:
            text = self._capture_text_with_uia()

        if not text.strip():
            text = app_info.get("title", "")

        return text

    def _capture_text_with_uia(self) -> str:
        try:
            from pywinauto import Desktop
            import win32gui

            hwnd = win32gui.GetForegroundWindow()
            app = Desktop(backend="uia").window(handle=hwnd)
            texts = []
            for element in app.descendants():
                try:
                    text = element.window_text()
                    if text and len(text.strip()) > 2:
                        texts.append(text.strip())
                except Exception:
                    pass
            return "\n".join(dict.fromkeys(texts))
        except Exception as error:
            log.debug(f"UIA read failed: {error}")
            return ""
