import queue
import threading
import traceback

from .config import log


class IngestionPipeline:
    """
    Receives raw events (screen), runs Groq extraction,
    and stores results in SQLite + Qdrant.
    """

    def __init__(self, db, vector_store, groq):
        self.db = db
        self.vs = vector_store
        self.groq = groq
        self._queue = queue.Queue()
        self._last_screen_content = ""
        threading.Thread(target=self._worker, daemon=True, name="Ingestion").start()

    def ingest(self, event: dict):
        if self._is_duplicate_screen_event(event):
            return
        self._queue.put(event)

    def _is_duplicate_screen_event(self, event: dict) -> bool:
        if event["type"] == "screen":
            content_hash = event["content"][:200]
            if content_hash == self._last_screen_content:
                return True
            self._last_screen_content = content_hash
        return False

    def _worker(self):
        while True:
            try:
                event = self._queue.get(timeout=1)
                self._process(event)
            except queue.Empty:
                pass
            except Exception as error:
                log.error(f"Ingestion error: {error}\n{traceback.format_exc()}")

    def _process(self, event: dict):
        log.info(
            f"Processing [{event['type']}] from {event.get('source_app', '')} - "
            f"{len(event['content'])} chars"
        )
        self.db.insert_event(event)

        extracted = self.groq.extract_entities(
            event["content"], event.get("source_app", "unknown")
        )
        if extracted.get("is_sensitive"):
            log.info("Skipping sensitive content")
            return

        self._store_extracted_data(event["id"], extracted)
        self._store_vector_record(event, extracted)

        log.info(
            f"Stored - entities: {len(extracted.get('entities', []))}, "
            f"summary: {extracted.get('summary', '')[:60]}"
        )

    def _store_extracted_data(self, event_id: str, extracted: dict):
        if extracted.get("entities"):
            self.db.insert_entities(event_id, extracted["entities"])
        if extracted.get("relationships"):
            self.db.insert_graph(event_id, extracted["relationships"])

    def _store_vector_record(self, event: dict, extracted: dict):
        summary = extracted.get("summary", "")
        entity_values = [entity["value"] for entity in extracted.get("entities", [])]
        embed_text = f"{summary}\n{event['content'][:800]}\n{' '.join(entity_values)}"

        self.vs.upsert(
            event_id=event["id"],
            text=embed_text,
            payload={
                "type": event["type"],
                "source_app": event.get("source_app", ""),
                "window_title": event.get("window_title", ""),
                "timestamp": event["timestamp"],
                "summary": summary,
            },
        )
