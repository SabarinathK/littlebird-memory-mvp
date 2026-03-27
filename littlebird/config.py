import logging
import os
import sys

from dotenv import load_dotenv


def load_config() -> dict:
    load_dotenv(override=True)
    groq_api_key = os.getenv("GROQ_API_KEY")
    return {
        "groq_api_key": groq_api_key,
        "groq_model": "llama-3.1-8b-instant",
        "whisper_model_size": "base",
        "screen_poll_interval": 6,
        "db_path": "memory.db",
        "collection_name": "littlebird_memory",
        "embedding_model": "all-MiniLM-L6-v2",
        "log_level": "INFO",
        "ignored_apps": [
            "Code.exe",
        ],
        "ignored_titles": ["password", "login", "sign in", "private"],
    }


CONFIG = load_config()


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, CONFIG["log_level"]),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("agent.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("agent")


log = configure_logging()
