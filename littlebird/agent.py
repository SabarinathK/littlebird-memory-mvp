import threading
import time

from .capture import ScreenCapture
from .config import CONFIG, log
from .llm import GroqClient
from .pipeline import IngestionPipeline
from .query import QueryEngine
from .storage import MemoryDB, VectorStore


class CaptureAgent:
    """
    Orchestrates screen capture and ingestion.
    Provides start/stop/pause/ask interface.
    """

    def __init__(self):
        log.info("Initialising Littlebird Windows Agent...")
        self.db = MemoryDB(CONFIG["db_path"])
        self.vector_store = VectorStore()
        self.groq = GroqClient()
        self.pipeline = IngestionPipeline(self.db, self.vector_store, self.groq)
        self.screen = ScreenCapture()
        self.query_engine = QueryEngine(self.db, self.vector_store, self.groq)
        self.paused = False
        self._screen_thread = None
        log.info("Agent ready")

    def start(self):
        self._screen_thread = threading.Thread(
            target=self._screen_loop, daemon=True, name="ScreenCapture"
        )
        self._screen_thread.start()
        log.info("Capture started - screen active")

    def _screen_loop(self):
        while True:
            if not self.paused:
                try:
                    event = self.screen.capture()
                    if event:
                        self.pipeline.ingest(event)
                except Exception as error:
                    log.debug(f"Screen capture error: {error}")
            time.sleep(CONFIG["screen_poll_interval"])

    def ask(self, question: str) -> str:
        return self.query_engine.ask(question)

    def pause(self):
        self.paused = True
        log.info("Capture paused")

    def resume(self):
        self.paused = False
        log.info("Capture resumed")

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
