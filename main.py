"""
Simple RAG API with endpoints for document ingestion, health checks, and querying
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
import io
from pypdf import PdfReader
import hashlib
from google.cloud import storage, aiplatform
import os
from pinecone import Pinecone, ServerlessSpec
from vertexai.language_models import TextEmbeddingModel
from dotenv import load_dotenv

load_dotenv()

# Set service account key path
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "rag-service-account.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s %(levelname)s %(message)s'
)

logger = logging.getLogger(__name__)

# Test vertex ai connection
aiplatform.init(project="simple-rag-485411", location="europe-west1")
logger.info("Vertex ai initialised")

# Initialise gcs client
client = storage.Client()
bucket_name = "simple-rag-bucket"
try:
    bucket = client.get_bucket(bucket_name)
    logger.info(f"Using existing bucket: {bucket_name}")
except Exception:
    logger.info("error accessing bucket")

# initialise pinecone client to uuse pinecone api
pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Vertex AI text-embedding-004 produces 768 dimensional vector
if not pinecone_client.has_index("simple-rag-index"):
    pinecone_client.create_index(
        name="simple-rag-index",
        dimension=768,
        metric="cosine",
        spec=ServerlessSpec(cloud="gcp", region="europe-west4")
    )
index = pinecone_client.Index("simple-rag-index")

# Load mebeddings model
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
async def embed_and_store_chunks(chunks):
    """
    Ebed chunks in batched and store in Pinecone vector db
    """
    BATCH_SIZE = 5  # Vertex AI supports up to 5 texts per request for text-embedding-004

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]

        texts = [chunk["data"] for chunk in batch]

        # Batch embeddings call
        embeddings = embedding_model.get_embeddings(texts)

        # prepare vectors for pinecone
        vectors = []
        for j, chunk in enumerate(batch):
            vectors.append({
                "id": chunk["id"],
                "values": embeddings[j].values,  # the actual embeddings vector
                "metadata": {
                    "text": chunk["data"],
                    "file_name": chunk["file_name"],
                    "content_type": chunk["content_type"],
                    "gcs_uri": chunk["gcs_uri"]
                }
            })
        
        # Upload to Pinecone
        index.upsert(vectors=vectors)
        logger.info(f"Uploaded batch {i//BATCH_SIZE + 1}: {len(vectors)} vectors")




app = FastAPI()

class IngestResponse(BaseModel):
    files_processed: int
    filenames: list[str]
    chunks_ingested: int
    chunks: list[dict]

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
            # 
            # should we check if content it not null before continuing
            # 
            content = await file.read()
            text_content = ""
            file_name = (file.filename or "").lower()
            text_splitter = None

            # Upload raw files to gcs
            blob = bucket.blob(file_name)
            blob.upload_from_string(content)    # works with bytes
            gcs_uri = f"gs://{bucket_name}/{file_name}"

            if file_name.endswith(".pdf"): 
                pdf_file = io.BytesIO(content)  # Create file-like stream object
                pdf_reader = PdfReader(pdf_file)    # parse pdf files from stream
                for page in pdf_reader.pages:
                    text_content += page.extract_text() or ""
                logger.info(f"Extracted {len(text_content)} from pdf: {file.filename}")
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

            elif file_name.endswith(".txt"):
                text_content = content.decode("utf-8")
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            
            if text_content and text_splitter:
                chunk_content = text_splitter.split_text(text_content)  # always returns a list
                for chunk in chunk_content:
                    all_chunks.append({
                        "id": hashlib.sha256(f"{file_name}-{chunk}".encode("utf-8")).hexdigest(),
                        "data": chunk,
                        "file_name": file_name,
                        "content_type": file.content_type or "",
                        "gcs_uri": gcs_uri
                    })
                processed_files.append(file.filename)

            # Check for duplicates (already embedded and in pinecone)
            ids = [chunk["id"] for chunk in all_chunks]
            exisiting = index.fetch(ids=ids)

            new_chunks = [chunk for chunk in all_chunks if chunk["id"] not in exisiting.get("vectors", {})]
            
            if new_chunks:
                logger.info(f"Embedding {len(new_chunks)} chunks...")
                await embed_and_store_chunks(new_chunks)
                logger.info("Embeddings stored in Pinecone")

        except Exception as e:
            logger.error(f"failed to process {file.filename}: {e}")

    return IngestResponse(
        files_processed=len(processed_files),
        filenames=processed_files,
        chunks_ingested=len(new_chunks),
        chunks=new_chunks
    )

@app.post("/query")
async def query(user_query: str):
    if not user_query or not user_query.strip():
        logger.error("user query empty")
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return user_query