"""
Simple RAG API with endpoints for document ingestion, health checks, and querying
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
import io
from pypdf import PdfReader

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
    logger.info("Ingest endpoint")
    processed_files = []
    all_chunks = []

    for file in files:
        try:
            content = await file.read()
            text_content = ""
            file_name = (file.filename or "").lower()
            text_splitter = None

            if file_name.endswith(".pdf"):    # Fallback incase content_type is wrong
                # Handle pdf
                pdf_file = io.BytesIO(content)  # Create file-like stream object
                pdf_reader = PdfReader(pdf_file)    # parse pdf files from stream
                for page in pdf_reader.pages:
                    text_content += page.extract_text() or ""
                logger.info(f"Extracted {len(text_content)} from pdf: {file.filename}")
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

            elif file_name.endswith(".txt"):
                # why did they check content type exists here but not above
                text_content = content.decode("utf-8")
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            
            if text_content and text_splitter:
                res = text_splitter.split_text(text_content)
                print(f"\nres=\n{res}\n")
                processed_files.append(file.filename)

        except Exception as e:
            logger.error(f"failed to process {file.filename}: {e}")
        
        # TODO: send chunks to embedding + vector db

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