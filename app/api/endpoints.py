# API route definitions
import os
import io
import logging
import shutil
from datetime import datetime
from flask import request
from flask_restx import Resource, reqparse
from werkzeug.utils import secure_filename
import time
import pytz
from datetime import datetime
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Optional, List, Dict, Any, Union
from pydantic import ValidationError

from ..config import Config
from ..database.chroma_client import ChromaManager
from ..database.mongo_client import MongoManager
from ..models import AIResponseOutput, UserQueryInput
from ..rag.chain import RAGChain
from ..rag.output_parser import CustomOutputParser
from ..utils.logging import AppLogger

# Parser for AI query input (used in AIquery endpoint)
ai_query_parser = reqparse.RequestParser()
ai_query_parser.add_argument('query', type=str, required=True, help='The natural language query for the AI')

class PDFUpload(Resource):
    """
    Handles PDF file uploads.
    On initialization, clears the upload directory and prepares it for new files.
    Uploaded PDFs are processed into chunks and embedded into ChromaDB.
    The original file is deleted after successful processing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Injected dependencies from app context
        self.config: Config = kwargs.get('config_obj')
        self.db_manager: MongoManager = kwargs.get('db_manager_obj')
        self.pdf_processor = kwargs.get('pdf_processor_obj')
        self.app_logger: AppLogger = kwargs.get('app_logger_obj')
        self.chroma_manager: ChromaManager = kwargs.get('chroma_manager_obj')

        # Directory where uploaded PDFs are temporarily stored
        self.pdf_upload_dir = self.config.UPLOAD_FOLDER

        # Text splitter used to divide PDF content into manageable chunks
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

        # Clean up existing upload directory if it exists
        if os.path.exists(self.pdf_upload_dir):
            self.app_logger.log_app_event('info',
                                          f'Existing PDF upload directory found. Deleting: {self.pdf_upload_dir}')
            shutil.rmtree(self.pdf_upload_dir)

        # Create a fresh upload directory
        os.makedirs(self.pdf_upload_dir, exist_ok=True)
        self.app_logger.log_app_event('info', f"PDF upload directory created/recreated: {self.pdf_upload_dir}")

    @CustomOutputParser.json_safe_response
    def post(self):
        # Initialize variables for tracking file and processing metadata
        filename = None
        pdf_filepath = None
        record_id_mongo = "Current file didn't get mongo id"
        start_time = datetime.utcnow()
        start = datetime.now()

        try:
            # Validate that a file was provided in the request
            if 'file' not in request.files:
                self.app_logger.log_app_event('warning', "No file provided", extra_data={'endpoint': '/papers/upload'})
                return CustomOutputParser.serialize_for_json({'success': False, 'message': 'No file provided', 'data': None}), 400

            file = request.files['file']

            # Validate that the file has a name
            if file.filename == '':
                self.app_logger.log_app_event('warning', "No file selected", extra_data={'endpoint': '/papers/upload'})
                return CustomOutputParser.serialize_for_json({'success': False, 'message': 'No file selected', 'data': None}), 400

            # Validate that the file type is allowed (PDF only)
            if not self.pdf_processor.allowed_file(file.filename, self.config.ALLOWED_EXTENSIONS):
                self.app_logger.log_app_event('warning', f"Invalid file type: {file.filename}")
                return CustomOutputParser.serialize_for_json({'success': False, 'message': 'Only PDF files are allowed', 'data': None}), 400

            # Secure the filename and save the file to the upload directory
            filename = secure_filename(file.filename)
            file_content = file.read()
            file_size = len(file_content)
            pdf_filepath = os.path.join(self.pdf_upload_dir, filename)

            with open(pdf_filepath, 'wb') as f:
                f.write(file_content)
            self.app_logger.log_app_event('info', f"PDF file saved temporarily to: {pdf_filepath}")

            # Prepare metadata for MongoDB record
            pdf_data = {
                'filename': filename,
                'original_filename': file.filename,
                'file_size': file_size,
                'upload_time': start,
                'mime_type': file.content_type or 'application/pdf',
                'pdf_filepath': pdf_filepath,
                'processed_in_chroma': False  # Will be updated to True after full ingestion
            }

            try:
                # Insert initial PDF metadata into MongoDB
                record_id_mongo = self.db_manager.insert_record_by_type('PDF', pdf_data)
                self.app_logger.log_app_event('info', f"Started processing PDF '{filename}'", extra_data={'mongo_id': record_id_mongo})

                # Read the PDF file into memory for text extraction
                with open(pdf_filepath, 'rb') as f:
                    pdf_file_stream = io.BytesIO(f.read())

                # Extract text from each page of the PDF
                page_texts = self.pdf_processor.extract_text_per_page(pdf_file_stream)

                # Create Document objects for each page with metadata
                page_documents = []
                for page_num, page_text in page_texts:
                    page_documents.append(Document(
                        page_content=page_text,
                        metadata={"source": filename, "mongo_id": record_id_mongo, "page_number": page_num}
                    ))

                # Split the documents into smaller chunks using the text splitter
                raw_chunks = self.text_splitter.split_documents(page_documents)

                # Normalize metadata and prepare final chunk list
                text_chunks = []
                for doc in raw_chunks:
                    metadata = doc.metadata.copy()
                    metadata.setdefault("mongo_id", record_id_mongo)
                    metadata.setdefault("page_number", None)
                    text_chunks.append(Document(page_content=doc.page_content, metadata=metadata))

                self.app_logger.log_app_event('info', f"Text split into {len(text_chunks)} chunks")

                # Remove any existing chunks in ChromaDB for this PDF
                self.chroma_manager.delete_chunks_by_mongo_id(str(record_id_mongo))
                self.app_logger.log_app_event('info', f"Deleted existing ChromaDB chunks for ID {record_id_mongo}")

                # Add new chunks to ChromaDB and get their IDs
                chroma_chunk_ids = self.chroma_manager.add_chunks_to_vector_db(
                    filename=filename,
                    text_chunks=text_chunks,
                    mongo_record_id=str(record_id_mongo)
                )
                self.app_logger.log_app_event('info', f"Inserted {len(chroma_chunk_ids)} chunks for PDF '{filename}'")

                # Update MongoDB record to mark it as processed and store chunk IDs
                self.db_manager.update_pdf_processed_status(record_id_mongo, True, chroma_chunk_ids)
                self.app_logger.log_app_event('info', f"Marked PDF record {record_id_mongo} as processed")

                # Delete the temporary PDF file from disk
                if pdf_filepath and os.path.exists(pdf_filepath):
                    os.remove(pdf_filepath)
                    self.app_logger.log_app_event('info', f"Deleted temporary PDF file: {pdf_filepath}")

                # Prepare response data for the client
                chunk_ids_list = [chunk.metadata.get("chunk_id") for chunk in text_chunks]

                response_data = {
                    'filename': filename,
                    'file_size': file_size,
                    'upload_time': pdf_data['upload_time'],
                    'mongo_record_id': record_id_mongo,
                    'chunk_ids': chunk_ids_list
                }

                self.app_logger.log_app_event('info', f"Upload completed for '{filename}'", extra_data={'record_id': record_id_mongo})
                return CustomOutputParser.serialize_for_json({'success': True, 'message': 'PDF uploaded and processed successfully', 'data': response_data}), 200

            except Exception as e:
                # Handle any error during PDF processing
                self.app_logger.log_app_event('error', f"PDF processing failed: {str(e)}", exc_info=True, extra_data={'filename': filename})
                if pdf_filepath and os.path.exists(pdf_filepath):
                    os.remove(pdf_filepath)
                    self.app_logger.log_app_event('info', f"Deleted temp file due to error: {pdf_filepath}")
                return CustomOutputParser.serialize_for_json({'success': False, 'message': f'Failed to process PDF: {str(e)}', 'data': None}), 500

        except Exception as e:
            # Handle unexpected errors during upload
            self.app_logger.log_app_event('error', f"Unexpected upload error: {str(e)}", exc_info=True)
            return CustomOutputParser.serialize_for_json({
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'data': None
            }), 500

class PDFFiles(Resource):
    """
    Resource for retrieving a list of uploaded PDF file records from MongoDB.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_manager: MongoManager = kwargs.get('db_manager_obj')
        self.app_logger: AppLogger = kwargs.get('app_logger_obj')

    @CustomOutputParser.json_safe_response
    def get(self):
        """
        Retrieves a list of PDF records from MongoDB (metadata only).
        """
        try:
            limit = request.args.get('limit', default=100, type=int)
            if limit <= 0 or limit > 1000:
                limit = 100

            # Use new unified collection method
            pdf_records = self.db_manager.get_log_records_by_collection('PDF', limit=limit)

            # Log to console only
            self.app_logger.log_app_event('info',
                                          f'Retrieved {len(pdf_records)} PDF records',
                                          extra_data={'count': len(pdf_records), 'limit': limit})

            return CustomOutputParser.serialize_for_json({
                'success': True,
                'ID': 'Multiple IDs',
                'message': f'Retrieved {len(pdf_records)} PDF file records',
                'data': pdf_records
            }), 200

        except Exception as e:
            self.app_logger.log_app_event('error',
                                          f'Error retrieving PDF records: {str(e)}', exc_info=True)
            return CustomOutputParser.serialize_for_json({
                'success': False,
                'ID': 'Multiple IDs',
                'message': f'Failed to retrieve PDF files: {str(e)}',
                'data': None
            }), 500

class PDFFile(Resource):
    """
    Resource for retrieving a single PDF file record by ID from MongoDB.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_manager: MongoManager = kwargs.get('db_manager_obj')
        self.app_logger: AppLogger = kwargs.get('app_logger_obj')

    @CustomOutputParser.json_safe_response
    def get(self, file_id):
        """
        Retrieves a single PDF record by ID from MongoDB.
        """
        try:
            pdf_record = self.db_manager.get_pdf_record_by_id(file_id)

            if not pdf_record:
                self.app_logger.log_app_event('warning',
                                              f'PDF record not found for ID: {file_id}',
                                              extra_data={'endpoint': f'/papers/{file_id}', 'method': 'GET'})
                return CustomOutputParser.serialize_for_json({
                    'success': False,
                    'ID': file_id,
                    'message': 'PDF file record not found',
                    'data': None
                }), 404

            self.app_logger.log_app_event('info',
                                          f'PDF record retrieved for ID: {file_id}',
                                          extra_data={'filename': pdf_record.get('filename'),
                                                      'endpoint': f'/papers/{file_id}'})

            return CustomOutputParser.serialize_for_json({
                'success': True,
                'ID': file_id,
                'message': 'PDF file record retrieved successfully',
                'data': pdf_record
            }), 200

        except Exception as e:
            self.app_logger.log_app_event('error',
                                          f'Error retrieving PDF by ID {file_id}: {str(e)}', exc_info=True)
            return CustomOutputParser.serialize_for_json({
                'success': False,
                'ID': file_id,
                'message': f'Failed to retrieve PDF file: {str(e)}',
                'data': None
            }), 500

class ApplicationLogs(Resource):
    """
    Resource for retrieving application log records from MongoDB.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_manager: MongoManager = kwargs.get('db_manager_obj')
        self.app_logger: AppLogger = kwargs.get('app_logger_obj')

    @CustomOutputParser.json_safe_response
    def get(self):
        """
        Retrieves only QUERY log records from MongoDB.
        This endpoint is fixed to return logs from the 'QUERY' collection.
        """
        try:
            limit = request.args.get('limit', default=100, type=int)
            if limit <= 0 or limit > 1000:
                limit = 100

            log_type = "QUERY"  # enforced — never comes from the user
            log_records = self.app_logger.get_mongodb_logs(log_type=log_type, limit=limit)

            self.app_logger.log_app_event('info',
                                          f"Retrieved {len(log_records)} QUERY log records.",
                                          extra_data={'count': len(log_records), 'limit': limit})

            response = CustomOutputParser.serialize_for_json({
                'success': True,
                'message': f"Retrieved {len(log_records)} QUERY log records",
                'logs': log_records
            })
            return response, 200

        except Exception as e:
            self.app_logger.log_app_event('error', f"Failed to retrieve QUERY logs: {str(e)}", exc_info=True)
            response = CustomOutputParser.serialize_for_json({
                'success': False,
                'message': f"Error retrieving QUERY logs: {str(e)}",
                'logs': []
            })
            return response, 500

class AIquery(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, *args, **kwargs)
        self.db_manager: MongoManager = kwargs.get('db_manager_obj')
        self.chroma_manager: ChromaManager = kwargs.get('chroma_manager_obj')
        self.app_logger: AppLogger = kwargs.get('app_logger_obj')
        self.config: Config = kwargs.get('config_obj')
        self.rag_chain: RAGChain = kwargs.get('rag_chain_obj')

    @CustomOutputParser.json_safe_response
    def post(self):
        query_text = ""
        start_overall_time = time.perf_counter()

        # ------------------ Step 1: Query validation ------------------
        try:
            query_text = request.args.get('query', type=str)

            if not query_text:
                # Console log: Missing query string
                self.app_logger.log_app_event('warning', 'Missing query string parameter "?query="', extra_data={
                    'endpoint': '/query', 'method': 'POST', 'status': 400
                })
                return CustomOutputParser.serialize_for_json({
                    'success': False,
                    'message': 'Missing "?query=..." in request.',
                    'data': None
                }), 400

            # Validate query format using Pydantic schema
            query_text = UserQueryInput(query=query_text).query

        except ValidationError as ve:
            # Console log: Pydantic validation failed
            self.app_logger.log_app_event('warning', f"Query validation failed: {ve.errors()}", exc_info=True,
                                          extra_data={
                                              'endpoint': '/query', 'method': 'POST', 'status': 400,
                                              'raw_data': query_text
                                          })
            return CustomOutputParser.serialize_for_json({
                'success': False,
                'message': f'Invalid query format. Details: {ve.errors()}',
                'data': None
            }), 400

        except Exception as e:
            # Console log: Unexpected validation exception
            self.app_logger.log_app_event('error', f"Unexpected validation error: {str(e)}", exc_info=True, extra_data={
                'endpoint': '/query', 'method': 'POST', 'status': 500
            })
            return CustomOutputParser.serialize_for_json({
                'success': False,
                'message': f'Internal error validating query: {str(e)}',
                'data': None
            }), 500

        # ------------------ Step 2: Retrieve latest PDF ------------------
        pdf_record = self.db_manager.get_latest_pdf_record()

        if not pdf_record:
            # Console log: No PDF found
            self.app_logger.log_app_event('warning', "No uploaded PDF found in MongoDB.")
            # MongoDB log: Query failed due to missing PDF
            self.app_logger.log_to_mongodb('QUERY', {
                'event': 'QueryFailed',
                'success': False,
                'timestamp': datetime.utcnow(),
                'user_query': query_text,
                'message': 'No PDF record found'
            })
            return CustomOutputParser.serialize_for_json({
                'success': False,
                'message': 'No document available for query.',
                'data': None
            }), 404

        record_filename = pdf_record.get('filename')
        pdf_record_id_mongo = str(pdf_record.get('_id'))

        if not pdf_record.get('processed_in_chroma', False):
            # Console log: Document not processed in ChromaDB
            self.app_logger.log_app_event('error', f"PDF '{record_filename}' not indexed in Chroma.")
            # MongoDB log: Query failed due to Chroma processing
            self.app_logger.log_to_mongodb('QUERY', {
                'event': 'QueryFailed',
                'success': False,
                'timestamp': datetime.utcnow(),
                'user_query': query_text,
                'filename': record_filename,
                'mongo_id': pdf_record_id_mongo,
                'message': 'PDF not processed in ChromaDB'
            })
            return CustomOutputParser.serialize_for_json({
                'success': False,
                'message': 'Document is not indexed yet. Please process it first.',
                'data': None
            }), 500

        # ------------------ Step 3: RAG invocation ------------------
        self.app_logger.log_app_event('info', f"Starting RAG query for: '{query_text}'")
        start_rag_invoke_time = time.perf_counter()
        try:
            llm_raw_output, retrieved_docs, scores = self.rag_chain.invoke(query_text,
                                                                           mongo_record_id=pdf_record_id_mongo)
            rag_chain_invoke_duration = time.perf_counter() - start_rag_invoke_time
            # ------------------ Step 4: Parse or fallback ------------------
            # If similarity is low, return fallback response
            if not self.rag_chain.is_context_relevant(retrieved_docs, scores):
                structured_response = CustomOutputParser.fallback_response(
                    pdf_filename=record_filename,
                    reason="Low similarity scores – no strong context found.",
                )
                # Console log: Weak context detected
                self.app_logger.log_app_event('warning', "Retrieved context was insufficient. Using fallback answer.")
            else:
                structured_response = CustomOutputParser.parse(
                    pdf_filename=record_filename,
                    llm_raw_output=llm_raw_output,
                    retrieved_docs=retrieved_docs,
                    scores=scores
                )
                # Console log: Successful parsing of model output
                self.app_logger.log_app_event('info', "Model output parsed successfully.")
        except Exception as e:
            #️ Console log: Failure while parsing LLM response
            self.app_logger.log_app_event('error', f"Exception during parsing: {str(e)}", exc_info=True)
            # MongoDB log: Query failure due to parse error
            self.app_logger.log_to_mongodb('QUERY', {
                'event': 'QueryFailed',
                'success': False,
                'timestamp': datetime.utcnow(),
                'user_query': query_text,
                'message': 'LLM output parsing failure'+str(e)
            })
            return CustomOutputParser.serialize_for_json({
                'success': False,
                'message': f"Failed to parse model output: {str(e)}",
                'data': None
            }), 500

        # ------------------ Step 5: Log to MongoDB ------------------
        overall_query_duration = time.perf_counter() - start_overall_time
        chunks = self.chroma_manager.get_chunks_by_mongo_id(pdf_record_id_mongo)

        # MongoDB log: Successful query
        query_mongo_id = self.app_logger.log_to_mongodb('QUERY', {
            'event': 'QueryProcessed',
            'success': structured_response.success,
            'timestamp': datetime.utcnow(),
            'user_query': query_text,
            'message': structured_response.message,
            'generated_answer': structured_response.generated_answer,
            'confidence_score': structured_response.confidence_score,
            'processing_metadata': {
                'llm_model': getattr(self.rag_chain, 'llm_name', 'unknown_model'),
                'pdf_record_id': pdf_record_id_mongo,
                'uploaded_pdf_filename': structured_response.filename,
                'chroma_collection_name': self.chroma_manager.collection_name
            },
            'performance_metrics': {
                'overall_query_duration': CustomOutputParser.format_duration(overall_query_duration),
                'rag_chain_invoke_duration': CustomOutputParser.format_duration(rag_chain_invoke_duration),
            },
            'source_citations': structured_response.source_citations,
            'retrieved_document_chunks': CustomOutputParser.build_retrieved_chunks_preview(chunks)
        })
        # Step 3: Optionally update the document to include 'query_id' field
        self.db_manager.update_log_field(query_mongo_id, {'query_id': query_mongo_id})

        # ------------------ Step 6: Return structured response ------------------
        return CustomOutputParser.serialize_for_json({
            'query_id': str(query_mongo_id),
            **structured_response.model_dump()
        }), 200
