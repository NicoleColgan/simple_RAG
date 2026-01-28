"""
Simple RAG API with endpoints for document ingestion, health checks, and querying
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
import logging
import os
from dotenv import load_dotenv
from services.storage import StorageService
from models import IngestResponse, QueryRequest, QueryResponse
from services.document_processor import DocumentProcessor
from services.embeddings import Embeddings
from services.vectorstore import VectorStore

# do we need this here???
load_dotenv()

# should we wrap in try/catch since some constructors have it
# Initialise services 
gcs_storage = StorageService()
embeddings = Embeddings()
vectorstore = VectorStore()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s %(levelname)s %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
def default():
    logger.info("Default endpoint")
    return "default endpoint"

@app.get("/health")
def health():
    return { "status": "OK"}

@app.post("/ingest", response_model=IngestResponse)
async def ingest(files: list[UploadFile] = File(...)):
    """Upload one or more files to ingest into the RAG system"""
    processed_files = []
    all_chunks = []

    for file in files:
        try:
            # 
            # should we check if content it not null before continuing
            # 
            content = await file.read()
            if not content:
                logger.warning(f"Skipping empty file: {file.filename}")
                continue
            
            filename = (file.filename or "").lower().strip()
            if not filename:    # is this even possible?
                logger.warning("Skipping file with no filename")
                continue
                
            gcs_uri = gcs_storage.upload_file(filename, content)

            if filename.endswith(".pdf"): 
                all_chunks = DocumentProcessor.process_pdf(content, filename, gcs_uri)
            elif filename.endswith(".txt"):
                all_chunks = DocumentProcessor.process_txt(content, filename, gcs_uri)
            else:
                logger.warning(f"invalid file format: {filename}... only pdfs and text files supported")
                continue

            processed_files.append(file.filename)
            vectors = embeddings.embed_chunks_in_batches(all_chunks)
            filtered_vectors = vectorstore.filter_existing_vectors(vectors)
            vectorstore.upload_to_pinecone(filtered_vectors)  

        except Exception as e:
            logger.error(f"failed to process {file.filename}: {e}")
            continue    # move to next file

    return IngestResponse(
        files_processed=len(processed_files),
        filenames=processed_files,
        chunks_ingested=len(filtered_vectors),
        chunks=filtered_vectors
    )

@app.post("/query")
async def query(query_request: QueryRequest):
    # do i still need below since im using pydantic model
    if not query_request or not query_request.strip():
        logger.error("user query empty")
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return QueryResponse(
        response=query_request.query
    )