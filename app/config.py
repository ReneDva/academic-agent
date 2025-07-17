import os
from dotenv import load_dotenv

class Config:
    """
    Configuration class that loads settings from environment variables.
    Provides structured access to MongoDB, app settings, Ollama and ChromaDB configs.
    """
    def __init__(self):
        load_dotenv()

        # MongoDB settings
        self.MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://mongodb:27017/')
        self.MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'Mongo_db')
        self.MONGODB_PDF_COLLECTION = os.getenv('MONGODB_PDF_COLLECTION', 'pdf_files')
        self.MONGODB_QUERY_COLLECTION = os.getenv('MONGODB_QUERY_COLLECTION', 'query_logs')

        # Application settings
        self.UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
        self.MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
        self.ALLOWED_EXTENSIONS = {'pdf'}

        # Logging settings
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

        # Ollama LLM settings
        self.OLLAMA_MODEL_NAME = os.getenv('OLLAMA_MODEL_NAME', 'my_llama3.2')
        self.OLLAMA_EMBEDDING_MODEL_NAME = os.getenv('OLLAMA_EMBEDDING_MODEL_NAME', 'nomic-embed-text')
        self.OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434/')

        # ChromaDB settings
        self.VECTOR_DB_PATH = os.getenv('VECTOR_DB_PATH', '/chroma/chroma')
        self.CHROMA_COLLECTION_NAME = os.getenv('CHROMA_COLLECTION_NAME', 'uploaded_pdf_vector_db')

        # General app flags
        self.DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
        self.PORT = int(os.getenv("PORT", 5000))
