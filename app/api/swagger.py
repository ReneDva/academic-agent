from flask_restx import Resource, reqparse, Api, fields
from werkzeug.datastructures import FileStorage
from ..api.endpoints import PDFUpload, PDFFiles, PDFFile, ApplicationLogs, AIquery
from ..models import UserQueryInput, AIResponseOutput
from ..rag.output_parser import CustomOutputParser

# File upload parser for /upload endpoint
pdf_upload_parser = reqparse.RequestParser()
pdf_upload_parser.add_argument(
    'file', location='files', type=FileStorage,
    required=True, help='PDF file to upload and process'
)

def register_swagger_resources(
    api_instance: Api,
    pdf_ns, logs_ns, ai_ns,
    pdf_upload_response_model,
    pdf_list_response_model,
    pdf_single_response_model,
    log_response_model,
    ai_query_response_model,
    error_model
):
    """
    Registers all decorated API resources to their respective namespaces,
    with Swagger documentation and marshaling.
    """

    # Upload PDF file
    class DecoratedPDFUpload(PDFUpload):
        @pdf_ns.expect(pdf_upload_parser)
        @pdf_ns.marshal_with(pdf_upload_response_model)
        @pdf_ns.response(200, "PDF uploaded and processed successfully", pdf_upload_response_model)
        @pdf_ns.response(400, "No file provided", error_model)
        @pdf_ns.response(400, "No file selected", error_model)
        @pdf_ns.response(400, "Only PDF files are allowed", error_model)
        @pdf_ns.response(500, "Failed to process PDF", error_model)
        @pdf_ns.response(500, "Unexpected error", error_model)
        @pdf_ns.doc(description="Upload a PDF file for extraction, chunking, and embedding into ChromaDB.")
        def post(self):
            return super().post()

    # List multiple PDF records
    class DecoratedPDFFiles(PDFFiles):
        @pdf_ns.doc(params={'limit': 'Max number of PDF records to return (default: 100, max: 1000)'})
        @pdf_ns.marshal_with(pdf_list_response_model)
        @pdf_ns.response(200, "Retrieved PDF file records", pdf_list_response_model)
        @pdf_ns.response(500, "Failed to retrieve PDF files", error_model)
        @pdf_ns.doc(description="Returns a list of uploaded PDF metadata records from MongoDB.")
        def get(self):
            return super().get()

    # Retrieve a single PDF record by ID
    class DecoratedPDFFile(PDFFile):
        @pdf_ns.doc(params={'file_id': 'MongoDB document ID of the PDF file'})
        @pdf_ns.marshal_with(pdf_single_response_model)
        @pdf_ns.response(200, "PDF file record retrieved successfully", pdf_single_response_model)
        @pdf_ns.response(404, "PDF file record not found", error_model)
        @pdf_ns.response(500, "Failed to retrieve PDF file", error_model)
        @pdf_ns.doc(description="Returns metadata for a specific PDF file record by Mongo ID.")
        def get(self, file_id):
            return super().get(file_id)

    # Retrieve QUERY logs only (Application-level)
    class DecoratedApplicationLogs(ApplicationLogs):
        @logs_ns.doc(params={'limit': 'Max number of QUERY log records to return (default: 100, max: 1000)'})
        @logs_ns.marshal_with(log_response_model)
        @logs_ns.response(200, "Retrieved QUERY log records", log_response_model)
        @logs_ns.response(500, "Error retrieving QUERY logs", error_model)
        @logs_ns.doc(description="Returns AI query logs (type: QUERY only).")
        def get(self):
            return super().get()

    # Run AI query against uploaded PDF
    class DecoratedAIquery(AIquery):
        @ai_ns.doc(params={'query': 'Enter your natural language question:'})
        @ai_ns.marshal_with(ai_query_response_model)
        @ai_ns.response(200, "AI query processed successfully", ai_query_response_model)
        @ai_ns.response(400, "Missing '?query=...'", error_model)
        @ai_ns.response(400, "Invalid query format", error_model)
        @ai_ns.response(500, "Internal error validating query", error_model)
        @ai_ns.response(404, "No document available for query", error_model)
        @ai_ns.response(500, "Document is not indexed yet", error_model)
        @ai_ns.response(500, "Failed to parse model output", error_model)
        @ai_ns.doc(
            description=
            """
            Submit a semantic question to analyze the latest uploaded academic PDF.  
            The system uses Retrieval-Augmented Generation (RAG) to locate context and generate a sourced AI response.
            """
        )
        def post(self):
            return super().post()

    return (
        DecoratedPDFUpload,
        DecoratedPDFFiles,
        DecoratedPDFFile,
        DecoratedApplicationLogs,
        DecoratedAIquery
    )
