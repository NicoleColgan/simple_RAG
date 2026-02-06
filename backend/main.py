"""
Simple RAG API with endpoints for document ingestion, health checks, and querying
"""
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import logging
from services.storage import StorageService
from models import IngestResponse, QueryRequest, QueryResponse
from services.document_processor import DocumentProcessor
from services.vertex_ai_service import VertexAIService
from services.vectorstore import VectorStore
from config import LOGGING_LEVEL, lOG_FORMAT

# Configure logging
logging.basicConfig(level=LOGGING_LEVEL, format=lOG_FORMAT)
logger = logging.getLogger(__name__)

try:
    # Initialise services 
    gcs_storage = StorageService()
    vertex_ai_service = VertexAIService()
    vectorstore = VectorStore()
except Exception as e:
    logger.error(f"Failed to initialise services: {e}", exc_info=True)
    raise   # crash - cant run without services

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
    vectors = []
    error_msg = None

    for file in files:
        try:
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
                all_chunks.extend(DocumentProcessor.process_pdf(content, filename, gcs_uri))
            elif filename.endswith(".txt"):
                all_chunks.extend(DocumentProcessor.process_txt(content, filename, gcs_uri))
            else:
                logger.warning(f"invalid file format: {filename}... only pdfs and text files supported")
                continue

            processed_files.append(file.filename)
        except Exception as e:
            logger.error(f"failed to process {file.filename}: {e}")
            continue    # move to next file
    try:
        all_chunks = vectorstore.filter_existing_vectors(all_chunks)
        if all_chunks:
            vectors = vertex_ai_service.embed_chunks_in_batches(all_chunks)
            vectorstore.upload_to_pinecone(vectors) 
    except Exception as e:
        logger.error(f"Failed to store chunks: {e}", exc_info=True)
        error_msg = e
    return IngestResponse(
        files_processed=len(processed_files),
        filenames=processed_files,
        chunks_ingested=len(all_chunks),
        chunks=all_chunks,
        error_msg=error_msg
    )

@app.post("/query")
def query(query_request: QueryRequest):
    # convert query to embedding
    vector = vertex_ai_service.get_single_embedding(query_request.query)

    # search pinecone for similar items
    similar = vectorstore.get_similar(vector, query_request.metadata_filter)

    if not similar:
        return QueryResponse(
            response="I dont have the context to answer that",
            sources=[],
            confidence=0.0
        )
    
    answer = vertex_ai_service.get_answer(similar, query_request.query)

    return QueryResponse(**answer)

@app.post("/query_stream")
def streamed_query(query_request: QueryRequest):
    vector = vertex_ai_service.get_single_embedding(query_request.query)

    similar = vectorstore.get_similar(vector, query_request.metadata_filter)

    if not similar:
        return QueryResponse(
            response="I dont have the context to answer that",
            sources=[],
            confidence=0.0
        )

    def stream_generator():
        for chunk in vertex_ai_service.get_answer(similar, query_request.query, stream=True):
            if chunk.text:
                yield chunk.text   

    return StreamingResponse(stream_generator(), media_type="text/event-stream") 