import re
import pytz
from functools import wraps
from flask import make_response
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Callable
from bson import ObjectId
from uuid import UUID
from decimal import Decimal
from langchain_core.documents import Document

from ..models import AIResponseOutput


class CustomOutputParser:
    """
    Parses LLM output into a structured AIResponseOutput model.
    Handles confidence extraction, formatting, source citation enrichment, and JSON sanitization.
    """

    @staticmethod
    def parse(
        pdf_filename: str,
        llm_raw_output: str,
        retrieved_docs: Optional[List[Document]] = None,
        scores: Optional[List[float]] = None
    ) -> AIResponseOutput:
        message = "The answer was successfully generated based on the provided context from the file: " + pdf_filename
        confidence_score = 0.0

        # Clean and normalize raw output
        answer_text = llm_raw_output.strip()
        answer_text = re.sub(r"Document\(.*?\)", "", answer_text)
        answer_text = re.sub(r"[ \t\r\n]+", " ", answer_text)
        answer_text = re.sub(r"\s{2,}", " ", answer_text).strip()

        # Extract embedded confidence
        confidence_match = re.search(r"Confidence[:\s]+(\d+\.?\d*)", answer_text, re.IGNORECASE)
        if confidence_match:
            try:
                raw_score = float(confidence_match.group(1))
                confidence_score = raw_score / 100 if raw_score > 1 else raw_score
                answer_text = re.sub(r"Confidence[:\s]+(\d+\.?\d*)", "", answer_text, flags=re.IGNORECASE).strip()
            except ValueError:
                message = "A response was generated using contextual information from the document: " + pdf_filename +". However, the confidence score could not be retrieved due to a parsing error."
                pass

        # Basic fallback from known phrases
        if re.search(r"(don't know|cannot find|no information found)", answer_text, re.IGNORECASE):
            answer_text = "No clear answer was found in the extracted documents."
            confidence_score = 0.0
            message = "The model did not find a direct answer in the source material."
            source_citations = []
        else:
            source_citations = []
            for idx, doc in enumerate(retrieved_docs or []):
                preview = re.sub(r'\s{2,}', ' ', re.sub(r'[\n\r\t]+', ' ', doc.page_content[:150])).strip()
                citation = {
                    "chunk_id": doc.metadata.get("chunk_id"),
                    "source_filename": doc.metadata.get("filename") or pdf_filename,
                    "mongo_id": doc.metadata.get("mongo_id"),
                    "content_preview": preview,
                    "page_number": doc.metadata.get("page_number") if isinstance(doc.metadata.get("page_number"), int) else None,
                    "score": scores[idx] if scores and idx < len(scores) else None
                }
                source_citations.append(citation)

        return AIResponseOutput(
            success=True,
            filename=pdf_filename,
            generated_answer=answer_text,
            confidence_score=confidence_score,
            message=message,
            source_citations=source_citations
        )

    @staticmethod
    def fallback_response(pdf_filename: str, reason: str = "No strong context found.") -> AIResponseOutput:
        """
        Creates a fallback response when context or LLM output is unreliable or missing.
        """
        return AIResponseOutput(
            success=True,
            filename=pdf_filename,
            generated_answer="I cannot find a definitive answer in the provided context.",
            confidence_score=0.0,
            message=reason,
            source_citations=[]
        )

    @staticmethod
    def format_duration(seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes} min {secs} sec"

    @staticmethod
    def format_timestamp_readable(timestamp: datetime) -> str:
        if timestamp.tzinfo is None:
            timestamp = pytz.utc.localize(timestamp)

        local_tz = pytz.timezone("Asia/Jerusalem")
        local_time = timestamp.astimezone(local_tz)
        return local_time.strftime('%H:%M:%S %d-%m-%Y') + f" ({local_tz.zone})"

    @staticmethod
    def build_retrieved_chunks_preview(chunks: List[Document]) -> List[Dict[str, Any]]:
        result = []
        for chunk in chunks:
            preview = chunk.page_content[:30]
            preview_clean = re.sub(r'[\n\r\t]+', ' ', preview).strip()
            preview_clean = re.sub(r'\s{2,}', ' ', preview_clean)
            result.append({
                "chunk_id": chunk.metadata.get("chunk_id"),
                "content_preview": preview_clean + "..."
            })
        return result

    @staticmethod
    def serialize_for_json(obj):
        """
        Recursively converts non-JSON-serializable objects into serializable formats.
        Preserves all values, including None, empty lists/dicts, and False/0.
        Does not filter or remove any fields — only transforms types like datetime, ObjectId, etc.
        """
        if isinstance(obj, dict):
            return {
                k: CustomOutputParser.serialize_for_json(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [
                CustomOutputParser.serialize_for_json(item)
                for item in obj
            ]
        elif isinstance(obj, datetime):
            return CustomOutputParser.format_timestamp_readable(obj)
        elif isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        elif hasattr(obj, '__dict__'):
            return CustomOutputParser.serialize_for_json(obj.__dict__)
        else:
            return obj

    @staticmethod
    def json_safe_response(func: Callable[..., Tuple[Any, int]]):
        @wraps(func)
        def wrapper(*args, **kwargs):
            raw_response = func(*args, **kwargs)
            if isinstance(raw_response, tuple) and len(raw_response) == 2:
                payload, status_code = raw_response
                processed = CustomOutputParser.serialize_for_json(payload)
                return processed, status_code
            return CustomOutputParser.serialize_for_json(raw_response)
        return wrapper
