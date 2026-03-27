import threading
import time
from typing import Any, Dict

from .capture import ScreenCapture
from .config import CONFIG, log
from .llm import GroqClient
from .pipeline import IngestionPipeline
from .query import QueryEngine
from .storage import MemoryDB, VectorStore


class CaptureAgent:
    """
    Orchestrates screen capture and ingestion.
    Provides lifecycle controls plus query access.
    """

    def __init__(self):
        log.info("Initialising Littlebird Windows Agent...")
        self.db = MemoryDB(CONFIG["db_path"])
        self.vector_store = VectorStore()
        self.groq = GroqClient()
        self.pipeline = IngestionPipeline(self.db, self.vector_store, self.groq)
        self.screen = ScreenCapture()
        self.query_engine = QueryEngine(self.db, self.vector_store, self.groq)
        self.paused = True
        self._screen_thread = None
        self._shutdown_event = threading.Event()
        self._state_lock = threading.Lock()
        self._capture_started_at = None
        self._captured_event_count = 0
        self._last_capture_at = None
        log.info("Agent ready")

    def start(self):
        with self._state_lock:
            if self._screen_thread and self._screen_thread.is_alive():
                self.paused = False
                log.info("Capture resumed")
                return

            self.paused = False
            self._shutdown_event.clear()
            self._capture_started_at = time.time()
            self._screen_thread = threading.Thread(
                target=self._screen_loop, daemon=True, name="ScreenCapture"
            )
            self._screen_thread.start()
            log.info("Capture started - screen active")

    def _screen_loop(self):
        while not self._shutdown_event.is_set():
            if not self.paused:
                try:
                    event = self.screen.capture()
                    if event:
                        self._captured_event_count += 1
                        self._last_capture_at = event["timestamp"]
                        self.pipeline.ingest(event)
                except Exception as error:
                    log.debug(f"Screen capture error: {error}")
            self._shutdown_event.wait(CONFIG["screen_poll_interval"])

    def ask(self, question: str) -> str:
        return self.query_engine.ask(question)

    def pause(self):
        self.paused = True
        log.info("Capture paused")

    def resume(self):
        if not self._screen_thread or not self._screen_thread.is_alive():
            self.start()
            return
        self.paused = False
        log.info("Capture resumed")

    def stop(self):
        with self._state_lock:
            if not self._screen_thread or not self._screen_thread.is_alive():
                self.paused = True
                return
            self.paused = True
            self._shutdown_event.set()
            self._screen_thread.join(timeout=2)
            self._screen_thread = None
            log.info("Capture stopped")

    def get_status(self) -> Dict[str, Any]:
        is_running = bool(self._screen_thread and self._screen_thread.is_alive())
        return {
            "running": is_running and not self.paused,
            "paused": self.paused,
            "thread_alive": is_running,
            "capture_started_at": self._capture_started_at,
            "last_capture_at": self._last_capture_at,
            "captured_event_count": self._captured_event_count,
            "recent_memory_count": len(self.db.recent_events(limit=10)),
        }

    def recent_summary(self) -> str:
        events = self.db.recent_events(limit=10)
        if not events:
            return "No memories captured yet."

        lines = []
        for event in events:
            timestamp = event["timestamp"][:16].replace("T", " ")
            lines.append(
                f"[{timestamp}] [{event['source_app']}] {event['content'][:80]}..."
            )
        return "\n".join(lines)
