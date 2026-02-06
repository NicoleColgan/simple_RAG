"""
Configuration and environment variables set up
"""
import os
from dotenv import load_dotenv

load_dotenv()

# GCP config
GCP_PROJECT_ID = "simple-rag-485411"
GCP_LOCATION = "europe-west1"
BUCKET_NAME = "simple-rag-bucket"

# Pinecone config
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY").strip()
PINECONE_INDEX_NAME = "simple-rag-index"
PINECONE_CLOUD = "gcp"
PINECONE_REGION = "europe-west4"
PINECONE_DIMENSION = 768
PINECONE_METRIC = "cosine"

# Vertex ai config
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_BATCH_SIZE = 5
LLM_MODEL = "gemini-2.5-flash"
LLM_TEMPERATURE = 0.2   # deterministic - grounded in facts
LLM_MAX_OUTPUT_TOKENS = 1100    # cost control - hard limit
LLM_MAX_RESPONSE_LIMIT = 1000   # soft limit - llm guidance
LLM_TOPK = 40   # hard cut off - only consider most likely k words

# Chunking config
PDF_CHUNK_SIZE = 800
PDF_CHUNK_OVERLAP = 100
TXT_CHUNK_SIZE = 500
TXT_CHUNK_OVERLAP = 50

# Logging
LOGGING_LEVEL = "INFO"
lOG_FORMAT = '%(asctime)s - %(name)s %(levelname)s %(message)s'