# Simple RAG System

A production-ready Retrieval-Augmented Generation (RAG) system built on Google Cloud Platform, featuring document ingestion, vector search, and agentic orchestration capabilities.

---

## Tech Stack

- **Backend**: Python, FastAPI (async)
- **Embeddings**: Vertex AI (text-embedding-004)
- **LLM**: Vertex AI (Gemini 1.5 Flash)
- **Vector Store**: Pinecone (serverless)
- **Storage**: Google Cloud Storage (GCS)
- **Deployment**: Cloud Run (planned)

---

## Project Roadmap

### Phase 1: Core RAG Service ✅
**Capabilities**
- Document upload (PDF, TXT)
- Text chunking and embedding
- Vector storage with metadata
- Query endpoint with grounded answers

**API Endpoints**
```http
POST /ingest        # Upload and process documents
POST /query         # Query with structured JSON response
POST /query_stream  # Query with streaming response
GET  /health        # Health check
```

### Phase 2: Agentic Orchestration 🚧
**Agent Architecture**
- **Planner Agent**: Decides which tools to use
- **Executor Agent**: Calls RAG service or external APIs
- **Verifier Agent**: Validates responses and enforces rules

**Framework**: LangGraph (explicit state machine orchestration)

### Phase 3: Cloud-Native Deployment 📋
**GCP Infrastructure**
- Cloud Run (API + frontend)
- Pub/Sub (async agent tasks)
- Secret Manager (credential management)

**Observability**
- Structured logging per agent step
- Request ID tracing
- Latency metrics

---

## Architecture

```
Client
  ↓
FastAPI (Cloud Run)
  ↓
Agent Orchestrator (LangGraph)
  ├─→ RAG Tool (Vertex AI + Pinecone)
  └─→ External APIs
  ↓
Pub/Sub (async tasks)
```

---

## Document Processing

### Chunking Strategy

The chunking strategy balances semantic coherence with retrieval quality.

#### Default Configuration (Recommended)
```python
RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
```

**Why this works:**
- ~500 characters ≈ one complete "thought"
- 10% overlap preserves sentence continuity
- Predictable and robust for most use cases

#### Content-Specific Settings

| Content Type | Chunk Size | Overlap | Rationale |
|-------------|-----------|---------|-----------|
| **Plain text / articles** | 500 | 50 | Standard balanced approach |
| **PDFs / manuals** | 800 | 100 | Messy extraction needs larger context |
| **FAQs / short answers** | 300 | 30 | Short, self-contained answers |
| **Code** | N/A | N/A | Use function/file-level splitting instead |

#### Tuning Guidelines

**Increase chunk_size if:**
- Retrieved chunks feel incomplete
- Documents are concept-heavy (tutorials, specs)
- Answers are almost correct but missing context

**Decrease chunk_size if:**
- Retrieval pulls in irrelevant context
- Documents contain many unrelated ideas
- Working with logs, FAQs, or Q&A content

**Overlap rule of thumb:**
> Overlap ≈ 10–20% of chunk_size

### RecursiveCharacterTextSplitter Behavior

This splitter preserves logical text structure by trying separators in order:

1. **Paragraphs** (`\n\n`)
2. **Lines** (`\n`)
3. **Spaces** (` `)
4. **Characters** (individual chars)

**Key behaviors:**
- Only moves to next separator if chunk exceeds `chunk_size`
- Merges adjacent chunks if combined length stays under limit
- Overlap only applies when forced to split mid-sentence/word
- Retries recursively on oversized chunks only

---

## Metadata & Deduplication

### Chunk Structure
```python
{
    "id": "<sha256-hash>",
    "data": "<chunk-text>",
    "filename": "<source-filename>",
    "gcs_uri": "gs://bucket/path"
}
```

### Deterministic ID Strategy

**Hash-based IDs:**
```python
hashlib.sha256(f"{filename}-{chunk_text}".encode("utf-8")).hexdigest()
```

**Advantages:**
- ✅ **Deduplication**: Same content = same ID
- ✅ **Deterministic**: Re-ingesting produces identical IDs
- ✅ **Idempotent**: Safe to re-run ingestion
- ✅ **Content-addressable**: ID represents actual content

**Why not UUIDs?**
- ❌ Same chunk ingested twice = duplicate vectors
- ❌ Database bloat from redundant embeddings
- ❌ Wasted storage and retrieval confusion

---

## Google Cloud Storage Setup

### Why GCS?

While the vector database handles similarity search, GCS provides:
- **Compliance**: Audit trail of source documents
- **Reprocessing**: Update embeddings when improving chunking
- **Debugging**: Compare chunks to original documents
- **Disaster recovery**: Restore if vector DB crashes
- **Cost**: ~€0.02/GB/month

### Configuration

| Setting | Value |
|---------|-------|
| **Project ID** | `simple-rag-485411` |
| **Region** | `europe-west1` (Belgium) |
| **Bucket** | `simple-rag-bucket` |
| **Service Account** | `simple-rag-service-account@simple-rag-485411.iam.gserviceaccount.com` |

### Setup Steps

#### 1. Create GCP Project
1. Navigate to https://console.cloud.google.com/
2. Create project: `simple-RAG`
3. Note the project ID: `simple-rag-485411`

#### 2. Enable Cloud Storage API
1. **APIs & Services** → **Enable APIs**
2. Search: "Cloud Storage API"
3. Click **Enable**

#### 3. Create Service Account
1. **IAM & Admin** → **Service Accounts** → **Create**
2. Name: `simple-rag-service-account`
3. Role: **Storage Object Admin**
4. Create JSON key → Save as `rag-service-account.json`

🚨 **Add key to .gitignore**
```gitignore
# Add to .gitignore immediately
rag-service-account.json
*.json
```

#### 4. Create Storage Bucket
1. **Cloud Storage** → **Buckets** → **Create**
2. Name: `simple-rag-bucket`
3. Location: Region → `europe-west1`
4. Storage class: Standard
5. Access control: Uniform (IAM only)
6. Public access: Prevent
7. Click **Create**

#### 5. Install Dependencies
```bash
pip install google-cloud-storage
```

---

## Ingestion Pipeline

### Flow Diagram
```
Upload → GCS Storage → Text Extraction → Chunking → Deduplication → Embedding → Pinecone
```

### 1. GCS Upload
- Authenticates via `rag-service-account.json`
- Checks if blob exists (skip redundant uploads)
- Returns GCS URI: `gs://simple-rag-bucket/filename`

### 2. Text Extraction
| Format | Tool | Method |
|--------|------|--------|
| **PDF** | pypdf.PdfReader | Page-by-page text extraction |
| **TXT** | Native | UTF-8 decoding |

### 3. Chunking
```python
# PDFs: Larger chunks for messy extraction
RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

# TXT: Standard configuration
RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
```

### 4. Deduplication
- Fetch existing IDs from Pinecone via batch `fetch()`
- Filter out already-embedded chunks
- Skip redundant embedding API calls

### 5. Embedding Generation
**Model**: Vertex AI `text-embedding-004`
- **Dimensions**: 768
- **Batch size**: 5 texts/call (Vertex AI limit)

**Output format:**
```python
{
    "id": "<sha256-hash>",
    "values": [0.123, ...],  # 768-dim vector
    "metadata": {
        "text": "<chunk_text>",
        "filename": "<source_file>",
        "gcs_uri": "gs://..."
    }
}
```

### 6. Vector Storage
**Pinecone Configuration:**
- **Index**: `simple-rag-index`
- **Spec**: Serverless (auto-scaling)
- **Region**: `europe-west4` (Amsterdam)
- **Metric**: Cosine similarity
- **Dimensions**: 768

---

## Query & Retrieval Pipeline

### Overview

The query endpoint uses RAG (Retrieval-Augmented Generation) to provide grounded answers by combining vector search with LLM generation.

### Request Format

**Standard Query Endpoint:**
```http
POST /query
Content-Type: application/json

{
  "query": "What is LangChain?",
  "metadata_filter": {
    "key": "filename",
    "operation": "eq",
    "value": "langchain_docs.pdf"
  }
}
```

**Streaming Query Endpoint:**
```bash
# Use -N flag to see streaming output
curl -N -X POST http://localhost:8000/query_stream \
  -H "Content-Type: application/json" \
  -d '{"query": "what is langchain?"}'
```

### Query Flow

```
User Query
  ↓
Pydantic Validation (StringConstraints: strip whitespace, minimum length)
  ↓
Embed Query (Vertex AI text-embedding-004)
  ↓
Vector Search (Pinecone) + Optional Metadata Filtering
  ↓
Retrieve Top-K Chunks (k=5)
  ↓
Filter by Similarity (> 70%)
  ↓
Construct Prompt (Question + Context)
  ↓
LLM Generation (Gemini 1.5 Flash via Vertex AI)
  ↓
Structured JSON Response
```

### Request Validation

**Query Model:**
- Uses `StringConstraints` to strip whitespace and enforce minimum length
- Validates input before processing

**Metadata Filter (Optional):**
- Defined as a Pydantic model
- **Key**: Must be one of `text`, `filename`, or `gcs_uri` (metadata fields stored in Pinecone)
- **Operation**: Either `eq` (equals) or `ne` (not equals)
- **Value**: Free-text string to match against the specified field

### Vector Search

**Configuration:**
```python
top_k = 5              # Retrieve top 5 chunks (optimal for small databases)
threshold = 0.70       # Filter chunks with similarity score > 70%
```

**Process:**
1. Generate embedding from user query using Vertex AI `text-embedding-004`
2. Query Pinecone with embedding + optional metadata filter
3. Filter out irrelevant chunks by only accepting scores > 70%
4. Pass retrieved chunks as context to LLM

**Metadata Filtering Example:**
```python
# Pinecone filter syntax
filter = {"filename": {"$eq": "specific_doc.pdf"}}  # Exact match
filter = {"text": {"$ne": "unwanted_text"}}        # Not equal
```

### LLM Configuration

**Model:** Gemini 1.5 Flash (via Vertex AI)

**Generation Config:**
```python
generation_config = {
    "temperature": 0.2,           # Low temperature for factual, deterministic responses
    "max_output_tokens": 1100,    # Prevents LLM from rambling and controls cost
    "response_mime_type": "application/json",
    "response_schema": schema     # Enforce structured JSON output
}
```

**Response Schema:**

The schema defines the JSON structure the LLM must return:

```python
RESPONSE_SCHEMA = {
            "type": "object",
            "description": "json response schema for model",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "Answer to the users question based on the context",
                    "nullable": False,
                    "maxLength": LLM_MAX_RESPONSE_LIMIT,  # soft limit - guidance for llm
                    "example": "Langchain is a framework for building your app with LLMs"
                },
                ...
                }
            },
            "required": ["response", "sources", "confidence"]
        }
```

**Schema Features:**
- **Type validation**: Ensures correct data types
- **Length constraints**: `maxLength` prevents excessively long responses
- **Nullable fields**: Marks optional fields with `nullable: True`
- **Examples**: Provides few-shot examples to guide the LLM
- **Required fields**: Enforces mandatory fields

### Response Handling

**Non-Streaming (`/query`):**
1. Call `generate_content()` with prompt and generation config
2. Deserialize LLM response from JSON string to dict
3. Unpack to Pydantic response model
4. Return structured JSON to user

**Example Response:**
```json
{
  "answer": "LangChain is a framework for developing applications powered by language models...",
  "sources": ["langchain_docs.pdf"]
}
```

**Streaming (`/query_stream`):**
1. Call `generate_content_stream()` for streaming response
2. Return iterable Generator object
3. Loop through each chunk in `main.py`
4. Return via FastAPI `StreamingResponse` object (Server-Sent Events)
5. Client sees incremental results in real-time

**Benefits of Streaming:**
- Lower perceived latency (results appear immediately)
- Better UX for long responses
- Client can display partial results while generation continues

### Modularization

The query pipeline is organized into modular services:

```
services/
├── prompts.py         # Response schemas and prompt templates
├── embeddings.py      # Vertex AI embedding & LLM calls
├── vectorstore.py     # Pinecone query operations
├── storage.py         # GCS operations
└── document_processor.py  # Text extraction & chunking
```

**Benefits:**
- Clear separation of concerns
- Easier testing and maintenance
- Reusable components across endpoints
- Simplified main.py endpoint logic

## Key Learnings

### FastAPI File Uploads
- `UploadFile`: FastAPI's file upload class with `.read()`, `.filename`, `.content_type`
- `File(...)`: Marks parameter as required from `multipart/form-data`
- Works together: `files: list[UploadFile] = File(...)`

### Pydantic Response Models
```python
class IngestResponse(BaseModel):
    files_processed: int
    filenames: list[str]
```
- Auto-validates output
- Generates OpenAPI docs
- Serializes to JSON
- Use `field: type | None = None` for optional fields

### Logging Configuration
```python
logging.basicConfig(
    level="INFO",  # DEBUG < INFO < WARNING < ERROR < CRITICAL
    format='%(asctime)s - %(name)s %(levelname)s %(message)s'
)
```