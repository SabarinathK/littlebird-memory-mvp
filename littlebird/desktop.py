import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .agent import CaptureAgent
from .config import log


class LittlebirdDesktopAPI:
    def __init__(self, agent: CaptureAgent):
        self._agent = agent

    def get_status(self):
        return self._agent.get_status()

    def start_capture(self):
        self._agent.resume()
        return self._agent.get_status()

    def pause_capture(self):
        self._agent.pause()
        return self._agent.get_status()

    def stop_capture(self):
        self._agent.stop()
        return self._agent.get_status()

    def recent_memory(self):
        return {
            "summary": self._agent.recent_summary(),
            "events": self._agent.db.recent_events(limit=20),
        }

    def ask(self, question: str):
        question = (question or "").strip()
        if not question:
            return {"question": question, "answer": "Please enter a question."}
        return {"question": question, "answer": self._agent.ask(question)}


class DesktopRequestHandler(BaseHTTPRequestHandler):
    server_version = "LittlebirdDesktop/0.1"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            return self._write_json(self.server.api.get_status())
        if parsed.path == "/api/recent":
            return self._write_json(self.server.api.recent_memory())
        return self._serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        payload = self._read_json_body()

        if parsed.path == "/api/capture/start":
            return self._write_json(self.server.api.start_capture())
        if parsed.path == "/api/capture/pause":
            return self._write_json(self.server.api.pause_capture())
        if parsed.path == "/api/capture/stop":
            return self._write_json(self.server.api.stop_capture())
        if parsed.path == "/api/chat":
            question = payload.get("question", "") if isinstance(payload, dict) else ""
            return self._write_json(self.server.api.ask(question))

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _serve_static(self, path: str):
        web_root = self.server.web_root
        requested = "index.html" if path in ("", "/") else path.lstrip("/")
        file_path = (web_root / requested).resolve()
        if not str(file_path).startswith(str(web_root.resolve())) or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        content_type = self._guess_content_type(file_path.suffix.lower())
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def _guess_content_type(self, suffix: str) -> str:
        mapping = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
        }
        return mapping.get(suffix, "application/octet-stream")

    def _write_json(self, payload, status: int = HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        log.debug("Desktop server: " + format % args)


class DesktopHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, api, web_root):
        super().__init__(server_address, RequestHandlerClass)
        self.api = api
        self.web_root = web_root


class DesktopServer:
    def __init__(self, api: LittlebirdDesktopAPI, host: str = "127.0.0.1", port: int = 0):
        self.api = api
        self.host = host
        self.port = port
        self._server: Optional[DesktopHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.web_root = Path(__file__).resolve().parent / "web"

    def start(self) -> str:
        self._server = DesktopHTTPServer(
            (self.host, self.port),
            DesktopRequestHandler,
            api=self.api,
            web_root=self.web_root,
        )
        actual_port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        url = f"http://{self.host}:{actual_port}/index.html"
        log.info(f"Desktop app available at {url}")
        return url

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
            self._thread = None


class DesktopApp:
    def __init__(self, agent: CaptureAgent):
        self._agent = agent
        self._api = LittlebirdDesktopAPI(agent)
        self._server = DesktopServer(self._api)

    def run(self):
        url = self._server.start()
        try:
            import webview
        except ImportError as error:
            self._server.stop()
            raise RuntimeError(
                "pywebview is required for desktop mode. Install it with `pip install pywebview`."
            ) from error

        webview.create_window(
            "Littlebird Desktop",
            url,
            width=1320,
            height=860,
            min_size=(1100, 720),
            text_select=True,
        )
        webview.start(debug=False)
        self._server.stop()
        self._agent.stop()
