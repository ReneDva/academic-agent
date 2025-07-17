from typing import List, Optional, Tuple
import time
from datetime import datetime
from langchain_core.documents import Document
from langchain_core.runnables import (
    RunnableParallel, RunnablePassthrough, RunnableLambda
)

from ..config import Config
from ..utils.logging import AppLogger
from langchain_ollama import OllamaLLM
from ..database.chroma_client import ChromaManager


class RAGChain:
    """
    RAGChain orchestrates retrieval + generation pipeline using ChromaDB and Ollama LLM.
    """

    def __init__(self, chroma_manager_instance: "ChromaManager", prompt: "PromptTemplate", app_logger: "AppLogger"):
        self.chroma_manager = chroma_manager_instance
        self.prompt = prompt
        self.app_logger = app_logger
        self.llm = self._initialize_ollama_llm()
        self.llm_name = self.llm.model if self.llm else "unknown"
        self.app_logger.log_app_event('info', "RAGChain initialized.")

    def _initialize_ollama_llm(self, retries=10, delay=10):
        """
        Initializes Ollama LLM with retry logic and connectivity test.
        """
        config = Config()
        base_url = config.OLLAMA_BASE_URL
        model_name = config.OLLAMA_MODEL_NAME

        for i in range(retries):
            try:
                self.app_logger.log_app_event('info', f"Attempt {i + 1}/{retries}: Initializing model '{model_name}' at {base_url}")
                ollama_llm_instance = OllamaLLM(base_url=base_url, model=model_name)
                ollama_llm_instance.invoke("Hi")  # Basic connectivity test
                return ollama_llm_instance
            except Exception as e:
                self.app_logger.log_app_event('error', f"Model init failed on attempt {i + 1}: {e}", exc_info=True)
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    self.app_logger.log_app_event('critical', f"Model '{model_name}' failed after {retries} attempts.")
                    raise ConnectionError(f"Could not connect to model '{model_name}'") from e
        return None

    def is_context_relevant(self, retrieved_docs: Optional[List[Document]], scores: Optional[List[float]],
                            threshold: float = 0.4) -> bool:
        """
        Determines whether the retrieved context is meaningful enough to parse.

        Returns False if no documents or scores are available,
        or if the top similarity score is below threshold.
        """
        if not retrieved_docs or not scores:
            return False
        return max(scores) >= threshold

    def invoke(self, question: str, mongo_record_id: Optional[str] = None) -> Tuple[str, List[Document], List[float]]:
        """
        Executes RAG flow: retrieve relevant chunks, generate answer with LLM.

        Returns:
            answer (str), enriched_chunks (List[Document]), similarity_scores (List[float])
        """
        self.app_logger.log_app_event('info', f"RAG invoked for question: '{question}' (Mongo ID: {mongo_record_id})")

        if not self.chroma_manager or not self.chroma_manager.vector_db:
            raise ValueError("ChromaDB manager missing.")

        # Setup filter for the specific MongoDB record
        filter_dict = {"mongo_id": str(mongo_record_id)} if mongo_record_id else {}
        search_kwargs = {"filter": filter_dict}

        # Prepare retriever and chain
        retriever = self.chroma_manager.get_retriever(search_kwargs=search_kwargs)

        rag_chain = (
            RunnableParallel(
                context=retriever,
                question=RunnablePassthrough()
            )
            | RunnableParallel(
                answer=(
                    RunnableParallel(
                        context=RunnableLambda(lambda x: [doc.page_content for doc in x["context"]]),
                        question=RunnablePassthrough()
                    )
                    | self.prompt
                    | self.llm
                ),
                retrieved_docs=RunnableLambda(lambda x: x["context"])
            )
        )

        chain_output = rag_chain.invoke(question)
        final_answer = chain_output.get("answer", "")

        # Retrieve chunks again with scores for filtering
        docs_and_scores = self.chroma_manager.vector_db.similarity_search_with_score(
            query=question,
            filter=filter_dict
        )

        enriched_documents: List[Document] = []
        similarity_scores: List[float] = []

        for doc, score in docs_and_scores:
            metadata = {
                "mongo_id": str(mongo_record_id),
                "filename": doc.metadata.get("source", "unknown"),
                "page_number": doc.metadata.get("page_number"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "score": score
            }
            enriched_documents.append(Document(page_content=doc.page_content, metadata=metadata))
            similarity_scores.append(score)

        self.app_logger.log_app_event('info', "RAG pipeline completed.")
        return final_answer, enriched_documents, similarity_scores
