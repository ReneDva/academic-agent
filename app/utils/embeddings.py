import os
import shutil
from typing import TYPE_CHECKING
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

from app.config import Config

if TYPE_CHECKING:
    from app.utils.logging import AppLogger


def get_embedding_function(model_name: str, app_logger: "AppLogger") -> OllamaEmbeddings:
    """
    Initializes and returns an Ollama embedding function for ChromaDB.

    Args:
        model_name (str): Name of the embedding model.
        app_logger (AppLogger): Logging utility.

    Returns:
        OllamaEmbeddings: Embedding function for use with ChromaDB.
    """
    try:
        config = Config()
        base_url = config.OLLAMA_BASE_URL

        app_logger.log_app_event(
            'info',
            f"Initializing OllamaEmbeddings with model '{model_name}' at base URL: {base_url}"
        )
        return OllamaEmbeddings(base_url=base_url, model=model_name)

    except Exception as e:
        app_logger.log_app_event(
            'error',
            f"Failed to initialize OllamaEmbeddings with model '{model_name}': {e}",
            exc_info=True
        )
        app_logger.log_app_event(
            'error',
            "Ensure Ollama is running and the requested embedding model is pulled."
        )
        raise e
