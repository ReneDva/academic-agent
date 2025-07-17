"""
Flask PDF Upload Application with MongoDB Integration
This application provides endpoints for PDF upload, content extraction, and data retrieval
with comprehensive logging and Swagger documentation.
"""
import os
import logging
from datetime import datetime

# Flask and related imports
from flask import Flask, request, jsonify
from flask_restx import Api

# Application component imports
from .config import Config
from .database.mongo_client import MongoManager
from .utils.pdf_processor import PDFProcessor
from .utils.logging import AppLogger # ייבוא AppLogger שמתפקד כסינגלטון
from .models import initialize_models
from .api.swagger import register_swagger_resources
from .database.chroma_client import ChromaManager
from .rag.chain import RAGChain # Assuming RAGChain is now in this path
from .rag.prompt_templates import FINAL_ANSWER_PROMPT


# --- Core component initialization ---

config = Config()

# Initialize AppLogger without MongoManager initially
app_logger = AppLogger(db_manager=None)

# Create MongoManager and attach AppLogger to it
db_manager = MongoManager(config, app_logger=app_logger)

# Update AppLogger with db_manager for MongoDB logging
app_logger.set_db_manager(db_manager)

# Initialize PDF processor
pdf_processor = PDFProcessor()

# --- AI and RAG pipeline initialization ---
chroma_manager = ChromaManager(config, app_logger)
rag_chain_instance = RAGChain(
    chroma_manager_instance=chroma_manager,
    prompt=FINAL_ANSWER_PROMPT,
    app_logger=app_logger
)

# --- Flask application setup ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
app.config.from_object(config)

# --- Swagger (Flask-RESTX) setup ---
api = Api(app,
          version='1.0',
          title='AI Research Assistant API',
          description='API for uploading research papers and querying them with AI',
          doc='/swagger/')

# Create namespaces for endpoint grouping
pdf_ns = api.namespace('papers', description='PDF document operations')
logs_ns = api.namespace('logs', description='Query logs')
ai_ns = api.namespace('query', description='AI-powered question answering')

# Load all data models for Swagger UI
(
    pdf_upload_response_model,
    pdf_list_response_model,
    pdf_single_response_model,
    log_response_model,
    ai_query_response_model,
    error_response_model,
    chroma_chunk_model
) = initialize_models(api)

# Register decorated endpoint classes
(
    DecoratedPDFUpload,
    DecoratedPDFFiles,
    DecoratedPDFFile,
    DecoratedApplicationLogs,
    DecoratedAIquery
) = register_swagger_resources(api, pdf_ns, logs_ns, ai_ns,
                               pdf_upload_response_model,
                               pdf_list_response_model,
                               pdf_single_response_model,
                               log_response_model,
                               ai_query_response_model,
                               error_response_model)

# --- Register endpoints with resource configurations ---

pdf_ns.add_resource(DecoratedPDFUpload, '/upload', methods=['POST'],
                    endpoint='pdf_upload',
                    resource_class_kwargs={
                        'config_obj': config,
                        'db_manager_obj': db_manager,
                        'pdf_processor_obj': pdf_processor,
                        'app_logger_obj': app_logger,
                        'chroma_manager_obj': chroma_manager
                    })

pdf_ns.add_resource(DecoratedPDFFiles, '/', methods=['GET'],
                    endpoint='pdf_files',
                    resource_class_kwargs={
                        'db_manager_obj': db_manager,
                        'app_logger_obj': app_logger
                    })

pdf_ns.add_resource(DecoratedPDFFile, '/<string:file_id>', methods=['GET'],
                    endpoint='pdf_file_by_id',
                    resource_class_kwargs={
                        'db_manager_obj': db_manager,
                        'app_logger_obj': app_logger
                    })

logs_ns.add_resource(DecoratedApplicationLogs, '/application', methods=['GET'],
                     endpoint='application_logs',
                     resource_class_kwargs={
                         'db_manager_obj': db_manager,
                         'app_logger_obj': app_logger
                     })

ai_ns.add_resource(DecoratedAIquery, '/', methods=['POST'],
                   endpoint='ai_query',
                   resource_class_kwargs={
                       'config_obj': config,
                       'db_manager_obj': db_manager,
                       'chroma_manager_obj': chroma_manager,
                       'app_logger_obj': app_logger,
                       'rag_chain_obj': rag_chain_instance,
                       'pdf_processor_obj': pdf_processor
                   })


# --- Health check endpoint ---

@app.route('/health')
def health_check():
    """System health check for uptime monitoring."""
    try:
        # Check MongoDB connectivity
        db_manager.client.admin.command('ping')

        # Check ChromaDB access
        chroma_manager.vector_db.get()

        app_logger.log_app_event('info', 'Health check passed')

        return {
            'status': 'healthy',
            'message': 'Application is running normally',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'vector_db': 'connected'
        }, 200

    except Exception as e:
        app_logger.log_app_event('error', f'Health check failed: {str(e)}', exc_info=True)
        return {
            'status': 'unhealthy',
            'message': f'Application has issues: {str(e)}',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'disconnected'
        }, 500


def setup_logging(config: Config):
    """Basic file logging using Python's standard logging module."""
    if not os.path.exists('./logs'):
        os.makedirs('./logs')

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler('./logs/app.log')]
    )


# --- Application entry point ---

if __name__ == '__main__':
    setup_logging(config)

    # Ensure upload folder exists
    if not os.path.exists(config.UPLOAD_FOLDER):
        os.makedirs(config.UPLOAD_FOLDER)

    app_logger.log_app_event('info', "Main application started.")

    app.run(debug=config.DEBUG, host='0.0.0.0', port=config.PORT)
