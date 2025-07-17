from flask_restx import fields, Api
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

def initialize_models(api_instance: Api):
    """
    Initializes and returns all Flask-RESTX models for Swagger documentation.
    These models define the structure of input and output objects exposed via the REST API.
    """

    # PDF Metadata Record
    pdf_record_model = api_instance.model('PDFRecord', {
        '_id': fields.String(description='MongoDB document ID', example='68723d8f32c81e6c95897cac'),
        'filename': fields.String(description='Processed filename', example='BOI.pdf'),
        'original_filename': fields.String(description='Original uploaded filename', example='original_BOI.pdf'),
        'file_size': fields.Integer(description='Size in bytes', example=123456),
        'upload_time': fields.String(description='Upload timestamp', example='2024-07-12T13:45:00'),
        'mime_type': fields.String(description='MIME type', example='application/pdf'),
        'pdf_filepath': fields.String(description='Temporary file path on server', example='/uploads/BOI.pdf'),
        'processed_in_chroma': fields.Boolean(description="Indicates whether all chunks of the PDF were "
                                                          "successfully embedded and stored in ChromaDB with metadata. "
                                                          "Will remain False until full ingestion is complete.",example=True)
    })

    # PDF Upload Response
    pdf_upload_data_model = api_instance.model('PDFUploadData', {
        'filename': fields.String(description='Processed filename', example='BOI.pdf'),
        'file_size': fields.Integer(description='File size in bytes', example=123456),
        'upload_time': fields.String(description='Upload timestamp', example='2024-07-12T13:45:00'),
        'mongo_record_id': fields.String(description='MongoDB document ID of the uploaded PDF', example='68723d8f32c81e6c95897cac'),
        'chunk_ids': fields.List(fields.String, description='List of chunk UUIDs generated during processing', example=[
            "a15d47e5-f32f-465b-81d8-26c13d9ea668",
            "ce7873fd-d8c7-4332-83fb-82fb707db005",
            "61cbdc22-5d79-426f-84a3-b0dd03c1abb6",
            "9ad9b064-225e-480f-9ab2-dbac032b3d83"])
    })

    # Chunk Metadata Record
    chroma_chunk_model = api_instance.model('ChromaChunk', {
        'chunk_id': fields.String(description='Unique identifier for the chunk', example='a15d47e5-f32f-465b-81d8-26c13d9ea668'),
        'page_number': fields.Integer(description='Page number in the original PDF', example=5),
        'mongo_id': fields.String(description='MongoDB document ID associated with the PDF', example='68723d8f32c81e6c95897cac'),
        'source': fields.String(description='Filename of the source PDF', example='BOI.pdf'),
        'page_content': fields.String(description='Text content of the chunk', example='This is the extracted text from page 5...')
    })

    # PDF Response Wrappers
    pdf_list_response_model = api_instance.model('PDFListResponse', {
        'success': fields.Boolean(description='Indicates if the request was successful', example=True),
        'message': fields.String(description='Optional message', example='Retrieved 3 PDF records'),
        'data': fields.List(fields.Nested(pdf_record_model), description='List of PDF metadata records')
    })

    pdf_single_response_model = api_instance.model('PDFFileResponse', {
        'success': fields.Boolean(description='Indicates if the request was successful', example=True),
        'message': fields.String(description='Optional message', example='PDF record retrieved successfully'),
        'data': fields.Nested(pdf_record_model, description='Single PDF metadata record')
    })

    pdf_upload_response_model = api_instance.model('PDFUploadResponse', {
        'success': fields.Boolean(description='Indicates if the upload was successful', example=True),
        'message': fields.String(description='Upload status message', example='PDF uploaded and processed successfully'),
        'data': fields.Nested(pdf_upload_data_model, description='Details of the uploaded PDF')
    })

    # Citation Source Model
    source_citation_model = api_instance.model('SourceCitation', {
        'chunk_id': fields.String(description='Chunk UUID', example='a15d47e5-f32f-465b-81d8-26c13d9ea668'),
        'source_filename': fields.String(description='PDF filename', example='report.pdf'),
        'mongo_id': fields.String(description='MongoDB document ID', example='64a1f2c3e4b0a2d1f9c12345'),
        'content_preview': fields.String(description='Chunk preview', example='Beneficial Ownership Informati...'),
        'page_number': fields.Integer(description='Page number in the source PDF', example=5),
        'score': fields.Float(description='Similarity score', example=0.87)
    })

    # Performance Metrics Model
    perf_metrics_model = api_instance.model('PerformanceMetrics', {
        'overall_query_duration': fields.String(description='Total query duration', example='1.23s'),
        'rag_chain_invoke_duration': fields.String(description='Duration of RAG invocation', example='0.89s')
    })

    # Metadata about the PDF and Model
    processing_metadata_model = api_instance.model('ProcessingMetadata', {
        'llm_model': fields.String(description='LLM name', example='my_llama3.2'),
        'pdf_record_id': fields.String(description='PDF MongoDB ID', example='64a1f2c3e4b0a2d1f9c12345'),
        'uploaded_pdf_filename': fields.String(description='Filename used', example='report.pdf'),
        'chroma_collection_name': fields.String(description='ChromaDB collection name', example='pdf_files')
    })

    # AI Query Response Model
    ai_query_response_model = api_instance.model('AIQueryResponse', {
        'query_id': fields.String(description='MongoDB log ID of the query', example='68723f8732c81e6c95897cad'),
        'success': fields.Boolean(description='Whether the query succeeded', example=True),
        'filename': fields.String(description='Source PDF filename', example='report.pdf'),
        'generated_answer': fields.String(description='AI-generated answer', example='The Corporate Transparency Act requires entities to report beneficial ownership information.'),
        'message': fields.String(description='System message (fallback, errors, etc.)', example=None),
        'confidence_score': fields.Float(description='Confidence score', example=0.92),
        'source_citations': fields.List(fields.Nested(source_citation_model), description='List of source citations')
    })

    # Query Log Record (QUERY type only)
    log_record_model = api_instance.model('LogRecord', {
        'query_id': fields.String(description='MongoDB log ID of the query', example='68723f8732c81e6c95897cad'),
        'event': fields.String(description='Event type: QueryProcessed / QueryFailed', example='QueryProcessed'),
        'success': fields.Boolean(description='Indicates if the request was successful', example=True),
        'timestamp': fields.String(description='Timestamp of the query event', example='2024-07-12T14:00:00'),
        'user_query': fields.String(description='Original user query submitted by the user', example='What is the Corporate Transparency Act?'),
        'generated_answer': fields.String(description='Answer generated by the AI model', example='The Corporate Transparency Act requires entities to report beneficial ownership information.'),
        'message': fields.String(description='System message or fallback reason', example=None),
        'confidence_score': fields.Float(description='Confidence score of the answer', example=0.92),
        'processing_metadata': fields.Nested(processing_metadata_model),
        'performance_metrics': fields.Nested(perf_metrics_model),
        'source_citations': fields.List(fields.Nested(source_citation_model), description='List of source citations used'),
        'retrieved_document_chunks': fields.List(fields.Raw(description='Preview of retrieved chunks'), example=[
            {
              "chunk_id": "a15d47e5-f32f-465b-81d8-26c13d9ea668",
              "content_preview": "Beneficial Ownership Informati..."
            },
            {
              "chunk_id": "ce7873fd-d8c7-4332-83fb-82fb707db005",
              "content_preview": "Beneficial Ownership Informati..."
            }])
    })

    # Response wrapper for GET /logs/application
    log_response_model = api_instance.model('ApplicationLogsResponse', {
        'success': fields.Boolean(description='Indicates if the request was successful', example=True),
        'message': fields.String(description='Optional message', example='Retrieved 5 log records'),
        'logs': fields.List(fields.Nested(log_record_model), description='List of log records')
    })

    # Error Response Model
    error_model = api_instance.model('ErrorResponse', {
        'success': fields.Boolean(description='Always false for errors',example=False),
        'message': fields.String(description='Error message describing the failure',example='No file provided in request'),
        'data': fields.Raw(description='Always null for errors',example=None)
    })

    return (
        pdf_upload_response_model,
        pdf_list_response_model,
        pdf_single_response_model,
        log_response_model,
        ai_query_response_model,
        error_model,
        chroma_chunk_model
    )

# Pydantic Input Schema for validating incoming queries
class UserQueryInput(BaseModel):
    query: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Natural language question to be answered by the AI engine"
    )


# Pydantic Output Schema for internal AI structured response
class AIResponseOutput(BaseModel):
    success: bool
    filename: Optional[str] = None
    message: Optional[str] = None
    generated_answer: Optional[str] = None
    confidence_score: Optional[float] = None
    source_citations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "filename": "BOI.pdf",
                "answer": "Companies can report BOI electronically using the BOI E-Filing portal.",
                "confidence_score": 0.92,
                "message": None,
                "source_citations": [
                    {
                        "chunk_id": "abc123",
                        "source_filename": "BOI.pdf",
                        "mongo_id": "686bab15a3c939a13dc01504",
                        "content_preview": "Reporting companies may access the portal at...",
                        "page_number": 5,
                        "score": 0.78
                    }
                ]
            }
        }
