# 📘 Academic Agent
## AI-Powered PDF Query Service
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) ![Docker Hub](https://img.shields.io/badge/Docker_Hub-0db7ed?style=for-the-badge&logo=docker&logoColor=white) ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white) ![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white) ![ChromaDB](https://img.shields.io/badge/ChromaDB-1B1B1B?style=for-the-badge&logo=data:image/svg%2Bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGZpbGw9Im5vbmUiIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iI2ZmZGUyZCIgZD0iTTE1LjkxNjU3NSAxOS41MmM0LjMyNjIyNSAwIDcuODMzMzI1IC0zLjM2NjggNy44MzMzMjUgLTcuNTE5OTc1IDAgLTQuMTUzMTc1IC0zLjUwNzEgLTcuNTE5OTc1IC03LjgzMzMyNSAtNy41MTk5NzUgLTQuMzI2MjI1IDAgLTcuODMzMzI1IDMuMzY2OCAtNy44MzMzMjUgNy41MTk5NzUgMCA0LjE1MzE3NSAzLjUwNzEgNy41MTk5NzUgNy44MzMzMjUgNy41MTk5NzVaIiBzdHJva2Utd2lkdGg9IjAuMjUiPjwvcGF0aD48cGF0aCBmaWxsPSIjMzI3ZWZmIiBkPSJNOC4wODMzMjUgMTkuNTJjNC4zMjYyMjUgMCA3LjgzMzMyNSAtMy4zNjY4IDcuODMzMzI1IC03LjUxOTk3NSAwIC00LjE1MzE3NSAtMy41MDcxIC03LjUxOTk3NSAtNy44MzMzMjUgLTcuNTE5OTc1QzMuNzU3MSA0LjQ4MDA1IDAuMjUgNy44NDY4NSAwLjI1IDEyLjAwMDAyNSAwLjI1IDE2LjE1MzIgMy43NTcxIDE5LjUyIDguMDgzMzI1IDE5LjUyWiIgc3Ryb2tlLXdpZHRoPSIwLjI1Ij48L3BhdGg+PHBhdGggZmlsbD0iI2ZmNjQ0NiIgZD0iTTE1LjkxNjYyNSAxMi4wMDAwMjVjMCA0LjE1MzIgLTMuNTA3MTI1IDcuNTE5OTI1IC03LjgzMzM3NSA3LjUxOTkyNVYxMi4wMDAwMjVoNy44MzMzNzVabS03LjgzMzM3NSAwYzAgLTQuMTUzMTc1IDMuNTA3MSAtNy41MTk5NzUgNy44MzMzNzUgLTcuNTE5OTc1djcuNTE5OTc1SDguMDgzMjVaIiBzdHJva2Utd2lkdGg9IjAuMjUiPjwvcGF0aD48L3N2Zz4=) ![Ollama](https://img.shields.io/badge/ollama-%23000000.svg?style=for-the-badge&logo=ollama&logoColor=white) ![LlaMA 3.2](https://img.shields.io/badge/LlaMA_3.2-0467DF?style=for-the-badge&logo=meta&logoColor=white) ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white) ![RAG](https://img.shields.io/badge/RAG-Retrieval--Augmented-6B21A8?style=for-the-badge) ![REST API](https://img.shields.io/badge/REST_API-005571?style=for-the-badge&logo=fastapi&logoColor=white) ![Swagger](https://img.shields.io/badge/Swagger-85EA2D?style=for-the-badge&logo=swagger&logoColor=black)

Academic Agent is a Flask-based REST API that allows users to upload academic PDF documents and ask natural language questions about their content.
It uses Retrieval-Augmented Generation (RAG) with LangChain and Ollama to generate accurate, context-aware answers.

---

## 🔧 Features

- 📤 **Upload PDF Files**: Submit PDFs via REST API
- 📄 **Content Extraction**: Extract and chunk document text
- 🧠 **AI Q&A**: Ask academic questions based on document context
- 🗃️ **MongoDB Storage**: Store metadata and logs
- 🧠 **ChromaDB Integration**: Use vector embeddings for retrieval
- 🧪 **Swagger Documentation**: Full API reference via browser
- 🪵 **Structured Logging**: Structured logging of queries and responses
- ❤️ **Health Monitoring**: Validate uptime and connections

---

## 🚀 Prerequisites
- Docker
---



## Running the Application

### Method 1: 🐳 Running with Docker Compose 
- *✅ Step 1: Clone the project*
```Bash
git clone https://github.com/ReneDva/academic-agent.git
cd academic-agent
```
- *✅ Step 2: Run with Docker Compose*
```Bash
docker compose up --build
```
This will build the Flask app locally and start all required services: MongoDB, ChromaDB, Ollama, and Mongo Express.


### Method 2: 🧠 Using a Prebuilt Image from Docker Hub (Recommended)
If you prefer not to build the Flask app locally, you can use the public image hosted on Docker Hub:
1. ✅ Replace build: . with image: in docker-compose.yml
```Yaml
flask_app:
  image: renedva/academic-agent:latest
  ports:
    - "5000:5000"
  ...
```
This allows you to run the app without needing the source code or Dockerfile locally — just the docker-compose.yml.
2. Then run:
```Bash
docker compose up
```
3. The application will start on `http://localhost:5000`


*Once containers are healthy and running, access:*
- Swagger UI: http://localhost:5000/swagger/
- MongoDB Admin Panel: http://localhost:8081

## 🔗 Access Points
- Swagger UI: http://localhost:5000/swagger/
- Mongo Express: http://localhost:8081

## 🧬 MongoDB Collections

# 📄 pdf_files
```Json
{
        "_id":"68723d8f32c81e6c95897cac",
        "filename": "BOI.pdf",
        "original_filename": "original_BOI.pdf",
        "file_size": 123456,
        "upload_time": "2024-07-12T13:45:00",
        "mime_type": "application/pdf",
        "pdf_filepath": "/uploads/BOI.pdf",
        "processed_in_chroma": "True"
}
```

# 📄 query_logs
```Json
{
        "query_id": "68723f8732c81e6c95897cad",
        "event": "QueryProcessed",
        "success": "True",
        "timestamp": "2024-07-12T14:00:00",
        "user_query": "What is the Corporate Transparency Act?",
        "generated_answer": "The Corporate Transparency Act requires entities to report beneficial ownership information.",
        "message": "The answer was successfully generated based on the provided context from the file: report.pdf",
        "confidence_score": 0.92,
        "processing_metadata": {
            "llm_model": "my_llama3.2",
            "pdf_record_id": "64a1f2c3e4b0a2d1f9c12345",
            "uploaded_pdf_filename": "report.pdf",
            "chroma_collection_name": "pdf_files"
        },
        "performance_metrics": {
            "overall_query_duration": "1.23s",
            "rag_chain_invoke_duration": "0.89s"
        },
        "source_citations": {
            "chunk_id": "a15d47e5-f32f-465b-81d8-26c13d9ea668",
            "source_filename": "report.pdf",
            "mongo_id": "64a1f2c3e4b0a2d1f9c12345",
            "content_preview": "Beneficial Ownership Informati...",
            "page_number": 5,
            "score": 0.87
        },
        "retrieved_document_chunks": [
            {
              "chunk_id": "a15d47e5-f32f-465b-81d8-26c13d9ea668",
              "content_preview": "Beneficial Ownership Informati..."
            },
            {
              "chunk_id": "ce7873fd-d8c7-4332-83fb-82fb707db005",
              "content_preview": "Beneficial Ownership Informati..."
            }
        ]
}
```
## API Endpoints

### 1. Upload PDF File

- **URL**: `POST /pdf/upload`
- **Description**: Upload a PDF file and extract its content
- **Content-Type**: `multipart/form-data`
- **Parameters**:
    - `file`: PDF file to upload

### 2. Get All PDF Files

- **URL**: `GET /pdf/files`
- **Description**: Retrieve list of all uploaded PDF files
- **Query Parameters**:
    - `limit`: Maximum number of records (default: 100)

### 3. Get Specific PDF File

- **URL**: `GET /pdf/files/{file_id}`
- **Description**: Retrieve specific PDF file record by ID
- **Parameters**:
    - `file_id`: MongoDB ObjectId of the PDF record

### 4. Get Application Logs

- **URL**: `GET /logs/application`
- **Description**: Retrieve application log records
- **Query Parameters**:
    - `limit`: Maximum number of records (default: 100)

### 5. Health Check

- **URL**: `GET /health`
- **Description**: Check application health status

## Swagger Documentation

Access the interactive API documentation at:
- **URL**: `http://localhost:5000/swagger/`
- **Features**:
    - Interactive API testing
    - Request/response examples
    - Parameter descriptions
    - Model schemas

## 🧠 Notes
- Ollama will automatically pull the required models (nomic-embed-text, llama3) and create a custom model my_llama3.2 during startup.
- Health checks ensure all services are ready before the app starts processing queries.
- You can customize environment variables in the docker-compose.yml file.


