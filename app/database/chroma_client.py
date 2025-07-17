import os
from uuid import uuid4
from typing import Optional, Any, List, Dict, TYPE_CHECKING
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.schema import Document

from ..utils.embeddings import get_embedding_function
from ..config import Config

if TYPE_CHECKING:
    from app.utils.logging import AppLogger

class ChromaManager:
    """
    Manages ChromaDB operations: connection, retrieval, insertion, and deletion of vector documents.
    """

    def __init__(self, config: Config, app_logger: "AppLogger"):
        self.config = config
        self.app_logger = app_logger
        self.embeddings_model: Optional[OllamaEmbeddings] = None
        self.vector_db: Optional[Chroma] = None
        self._connect()

    def _connect(self):
        """
        Initialize embedding model and connect to ChromaDB.
        Creates vector DB directory if missing.
        """
        try:
            self.embeddings_model = get_embedding_function(
                self.config.OLLAMA_EMBEDDING_MODEL_NAME, self.app_logger
            )

            if not os.path.exists(self.config.VECTOR_DB_PATH):
                os.makedirs(self.config.VECTOR_DB_PATH)
                self.app_logger.log_app_event('info', f"Created ChromaDB directory at: {self.config.VECTOR_DB_PATH}")

            self.vector_db = Chroma(
                persist_directory=self.config.VECTOR_DB_PATH,
                embedding_function=self.embeddings_model,
                collection_name=self.config.CHROMA_COLLECTION_NAME
            )

            self.collection_name = self.config.CHROMA_COLLECTION_NAME
            self.app_logger.log_app_event('info', f"Connected to ChromaDB at: {self.config.VECTOR_DB_PATH}")

        except Exception as e:
            self.app_logger.log_app_event('error', f"ChromaDB connection failed: {e}", exc_info=True)
            raise

    def get_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None):
        """
        Returns a ChromaDB retriever with optional search filters.
        """
        if not self.vector_db:
            self.app_logger.log_app_event('error', "ChromaDB not initialized.")
            raise ValueError("ChromaDB not initialized.")

        retriever = self.vector_db.as_retriever()
        if search_kwargs:
            retriever.search_kwargs = search_kwargs
        return retriever

    def get_chunks_by_mongo_id(self, mongo_record_id: str) -> List[Document]:
        """
        Fetches vectorized document chunks from ChromaDB by MongoDB record ID.
        """
        if not self.vector_db:
            self.app_logger.log_app_event('error', "ChromaDB not initialized.")
            raise ValueError("ChromaDB not initialized.")

        try:
            mongo_id_str = str(mongo_record_id)
            results = self.vector_db.get(where={"mongo_id": mongo_id_str})

            documents = [
                Document(page_content=doc_text, metadata=doc_metadata)
                for doc_text, doc_metadata in zip(results.get("documents", []), results.get("metadatas", []))
            ]

            self.app_logger.log_app_event('info', f"Retrieved {len(documents)} chunks for MongoDB ID: {mongo_id_str}")
            return documents

        except Exception as e:
            self.app_logger.log_app_event('error', f"Failed to fetch chunks for MongoDB ID {mongo_record_id}: {e}", exc_info=True)
            return []

    def add_chunks_to_vector_db(self, filename: str, text_chunks: List[Document], mongo_record_id: str) -> List[str]:
        """
        Inserts extracted chunks into ChromaDB with full metadata.
        Returns list of assigned chunk IDs.
        """
        if not self.vector_db:
            self.app_logger.log_app_event('error', "ChromaDB not initialized.")
            raise ValueError("ChromaDB not initialized.")

        if not text_chunks:
            self.app_logger.log_app_event('warning', f"No chunks provided for '{filename}' (MongoDB ID: {mongo_record_id})")
            return []

        for chunk in text_chunks:
            chunk.metadata["chunk_id"] = str(uuid4())
            chunk.metadata["filename"] = filename
            chunk.metadata["mongo_id"] = str(mongo_record_id)
            chunk.metadata["page_number"] = chunk.metadata.get("page_number") or chunk.metadata.get("parent_page_number")

        self.app_logger.log_app_event('debug', f"Chunk metadata preview: {text_chunks[0].metadata}")
        self.app_logger.log_app_event('info', f"Inserting {len(text_chunks)} chunks for file '{filename}'")

        try:
            generated_ids = self.vector_db.add_documents(text_chunks)

            if not generated_ids:
                self.app_logger.log_app_event('error', f"No chunk IDs returned for '{filename}'")
                raise RuntimeError("Chunks not saved to ChromaDB.")

            self.app_logger.log_app_event('info', f"Inserted {len(generated_ids)} chunks for '{filename}'. Sample IDs: {generated_ids[:5]}")

            for i, chunk in enumerate(text_chunks[:3]):
                self.app_logger.log_app_event('debug',
                    f"[Chunk {i + 1}] mongo_id={chunk.metadata.get('mongo_id')}, filename={chunk.metadata.get('filename')}, page={chunk.metadata.get('page_number')}"
                )

            return generated_ids

        except Exception as e:
            self.app_logger.log_app_event('error', f"Chunk insertion failed for '{filename}': {e}", exc_info=True)
            return []

    def delete_chunks_by_mongo_id(self, mongo_record_id: str):
        """
        Deletes all chunks in ChromaDB that match the given MongoDB record ID.
        """
        if not self.vector_db:
            self.app_logger.log_app_event('error', "ChromaDB not initialized.")
            raise ValueError("ChromaDB not initialized.")

        try:
            self.vector_db.delete(where={"mongo_id": mongo_record_id})
            self.app_logger.log_app_event('info', f"Deleted chunks for MongoDB ID: {mongo_record_id}")
        except Exception as e:
            self.app_logger.log_app_event('error', f"Chunk deletion failed for MongoDB ID {mongo_record_id}: {e}", exc_info=True)
            raise
