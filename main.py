"""
Simple RAG API with endpoints for document ingestion, health checks, and querying
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s %(levelname)s %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI()

class IngestResponse(BaseModel):
    files_processed: int
    filenames: list[str]

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
    # UploadFile is FastAPI’s class for uploaded files and provides .read(), .filename, .content_type, etc.
    # File(...) tells FastAPI to extract uploaded files from a multipart/form-data request body;
    # the ellipsis (...) means the field is required (i.e. it must be present in the request).

    processed_files = []

    for file in files:
        # read file conent
        content = await file.read()

        # TODO: Process the documents (chunk, embed, store in vector db)
        # For now, just track the file name
        processed_files.append(file.filename)

    return IngestResponse(
        files_processed=len(processed_files),
        filenames=processed_files
    )

@app.post("/query")
async def query(user_query: str):
    if not user_query or not user_query.strip():
        logger.error("user query empty")
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return user_query