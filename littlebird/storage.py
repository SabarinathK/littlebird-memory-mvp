import sqlite3
import threading
import uuid

import chromadb
from sentence_transformers import SentenceTransformer

from .config import CONFIG, log
from .utils import require, utc_now_iso


class MemoryDB:
    """
    Stores every captured event in SQLite.
    Schema:
        events  - raw screen events
        entities - extracted entities per event
        graph   - entity relationships (source -> relation -> target)
    """

    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        with self.lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id          TEXT PRIMARY KEY,
                    type        TEXT,
                    source_app  TEXT,
                    window_title TEXT,
                    content     TEXT,
                    timestamp   TEXT,
                    processed   INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS entities (
                    id          TEXT PRIMARY KEY,
                    event_id    TEXT,
                    entity_type TEXT,
                    value       TEXT,
                    timestamp   TEXT,
                    FOREIGN KEY(event_id) REFERENCES events(id)
                );

                CREATE TABLE IF NOT EXISTS graph (
                    id          TEXT PRIMARY KEY,
                    source      TEXT,
                    relation    TEXT,
                    target      TEXT,
                    event_id    TEXT,
                    timestamp   TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_events_ts   ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_entities_v  ON entities(value);
                CREATE INDEX IF NOT EXISTS idx_graph_src   ON graph(source);
            """
            )
            self.conn.commit()

    def insert_event(self, event: dict):
        with self.lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?)",
                (
                    event["id"],
                    event["type"],
                    event.get("source_app", ""),
                    event.get("window_title", ""),
                    event["content"],
                    event["timestamp"],
                    0,
                ),
            )
            self.conn.commit()

    def insert_entities(self, event_id: str, entities: list):
        with self.lock:
            for entity in entities:
                self.conn.execute(
                    "INSERT OR IGNORE INTO entities VALUES (?,?,?,?,?)",
                    (
                        str(uuid.uuid4()),
                        event_id,
                        entity["type"],
                        entity["value"],
                        utc_now_iso(),
                    ),
                )
            self.conn.commit()

    def insert_graph(self, event_id: str, relationships: list):
        with self.lock:
            for relationship in relationships:
                self.conn.execute(
                    "INSERT OR IGNORE INTO graph VALUES (?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()),
                        relationship["from"],
                        relationship["relation"],
                        relationship["to"],
                        event_id,
                        utc_now_iso(),
                    ),
                )
            self.conn.commit()

    def recent_events(self, limit: int = 20) -> list:
        with self.lock:
            cur = self.conn.execute(
                "SELECT type, source_app, window_title, content, timestamp "
                "FROM events ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [
                dict(zip([description[0] for description in cur.description], row))
                for row in cur.fetchall()
            ]

    def search_entities(self, query: str, limit: int = 10) -> list:
        with self.lock:
            cur = self.conn.execute(
                "SELECT DISTINCT value, entity_type, timestamp FROM entities "
                "WHERE value LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit),
            )
            return [
                dict(zip([description[0] for description in cur.description], row))
                for row in cur.fetchall()
            ]

    def graph_neighbors(self, entity: str, limit: int = 10) -> list:
        with self.lock:
            cur = self.conn.execute(
                "SELECT source, relation, target, timestamp FROM graph "
                "WHERE source LIKE ? OR target LIKE ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (f"%{entity}%", f"%{entity}%", limit),
            )
            return [
                dict(zip([description[0] for description in cur.description], row))
                for row in cur.fetchall()
            ]


class VectorStore:
    """
    Stores event embeddings in ChromaDB for semantic search.
    Runs locally with persistence (no Docker needed).
    """

    def __init__(self):
        require("chromadb")
        require("sentence_transformers", "sentence-transformers")

        self.model = SentenceTransformer(CONFIG["embedding_model"])
        self.collection_name = CONFIG["collection_name"]
        self.lock = threading.Lock()
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )
        log.info("ChromaDB initialized (persistent local mode)")

    def upsert(self, event_id: str, text: str, payload: dict):
        with self.lock:
            embedding = self.model.encode(text).tolist()
            self.collection.upsert(
                ids=[event_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[payload],
            )

    def search(self, query: str, limit: int = 5) -> list:
        with self.lock:
            embedding = self.model.encode(query).tolist()
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=limit,
            )
            return self._format_search_results(results)

    def _format_search_results(self, results: dict) -> list:
        output = []
        for index in range(len(results["ids"][0])):
            item = {
                "score": (
                    results["distances"][0][index]
                    if "distances" in results
                    else None
                ),
                "text": results["documents"][0][index],
                **results["metadatas"][0][index],
            }
            output.append(item)
        return output
