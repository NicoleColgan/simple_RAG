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
curl -N -X POST http://localhost:8000/query_stream -H "Content-Type: application/json" -d "{\"query\": \"What is langchain?\"}"
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
  "response": "LangChain is a framework designed to simplify the development of applications that leverage large language models (LLMs). It provides a unified framework for managing tasks and abstracts the complexity associated with directly integrating LLMs into an application. It is a versatile framework for building applications that efficiently utilize LLMs.",
  "sources": [
    "f1.pdf"
  ],
  "confidence": 1
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
├── vertex_ai_service.py      # Vertex AI embedding & LLM calls
├── vectorstore.py     # Pinecone query operations
├── storage.py         # GCS operations
└── document_processor.py  # Text extraction & chunking
```

**Benefits:**
- Clear separation of concerns
- Easier testing and maintenance
- Reusable components across endpoints
- Simplified main.py endpoint logic

--

## Containerisation
```cmd
docker build -t "simple-rag" .    
docker run --rm -p 8000:8000 -v "${PWD}/rag-service-account.json:/app/rag-service-account.json:ro" --env-file .env simple-rag:latest
```
Mount the service key as read-only and inject the env file at runtime. This keeps our secrets completely out of the image so they can't be leaked or stolen if the image is shared

### Docker Architecture & Security

- **Multi-stage Build:** We use a multi-stage build for efficiency and security. Think of each stage as a temporary "mini-computer" that exists only to do its specific task. When we hit a new `FROM` statement, the previous computer shuts down, but Docker lets us reach back into its "hard drive" to grab only the finished files we need. This keeps the final image tiny and removes build tools (compilers, etc.) that aren't needed in production.
- **Hardened Base Images:** We use `dhi.io/python:3-debian12-dev` for building and `dhi.io/python:3-debian12` for running. 
    - **Debian 12** is the current stable standard, ensuring high compatibility for Python libraries.
    - **Hardened Images** are pre-scanned to have nearly zero security vulnerabilities (CVEs).
    - The **-dev** version has the "muscles" (compilers/pip) needed to install libraries as the root user, while the final image is locked down for safety.
- **Dependency Optimization:** We use the `--user` flag to install libraries into a specific "suitcase" folder (`.local`) that is easy to move between stages. We use `--no-cache-dir` to keep the build stage small. 
    > **Does this matter in multi-stage?** Yes! Even though the builder stage is thrown away, a smaller builder stage makes the build process faster, uses less RAM, and saves disk space on your laptop or CI/CD server while it's working.
- **Clean Runtime Environment:** The final stage uses a fresh `/app` directory and runs as a restricted `nonroot` user. This means even if the app is compromised, the attacker has no "Admin" rights and no shell access.
- **Path Mapping:** Because we "teleported" our libraries to a non-standard directory (`/home/nonroot/.local`), we use `ENV PATH` to tell Python where to find them. The `$PATH` part ensures we add to the search list rather than replacing it.
- **Network Binding:** We run Uvicorn with `--host 0.0.0.0`. 
    - **Why?** Inside a container, `127.0.0.1` means "listen only to myself." `0.0.0.0` is a "catch-all" that tells the container to accept requests from the outside (your computer).
- **Fixed Port Mapping:** We explicitly lock Uvicorn to `--port 8000`. This ensures that our `docker run -p 8000:8000` command always has a reliable "bridge" to the app inside.

---

## Deploying to cloud run

**What is Cloud Run?**
Cloud Run is a managed compute platform that allows you to run containers without worrying about maintaining servers. It automatically scales up and down based on traffic—even to zero when the service is idle.

**Why Cloud Run for a RAG app?**
* **True Pay-Per-Use**: In the default "Request-based billing" mode, you are only charged when your container is actually processing a request (i.e., when someone calls your endpoint) plus a tiny bit of startup/shutdown time. You don't pay while the service is sitting idle.
* **Security**: Natural integration with Google Secret Manager and IAM (Identity and access management)
* **Scaling**: RAG apps can be memory-intensive. Cloud run allows you to precisely allocate CPU and RAM. We used 2GiB RAM which is perfect for avoiding `Out of Memory` errors for processing PDFs, and 2 CPUs to ensure the service can handle concurrent requests without lagging (not implemented yet)

### 1. Infrastructure Setup

**Initialise Gcloud**
```bash
# Login to your Google account
gcloud auth login

# Set your project ID
gcloud config set project simple-rag-485411
```

**Create Artifact Registry**
Create a Docker repository in the `europe-west1` (Belgium) region to store the Docker image
```bash
gcloud artifacts repositories create my-rag-repo --repository-format=docker --location=europe-west1 --description="Docker repository for rag app"
```

### 2. Containerisation and Registry

**Build the Image**
Build image for `linux/amd64` to ensure compatibility with Google's server architecture. This is usually the same format Windows uses, but it's better to specify it explicitly. You can check the architecture with `docker image inspect`.
```bash
docker build --platform linux/amd64 -t europe-west1-docker.pkg.dev/simple-rag-485411/my-rag-repo/simple-rag:v1 .
```

**Authenticate Docker and Push**
Since Docker will be interacting with the registry (not gcloud), we need to authenticate Docker.
The command below configures Docker to use gcloud credentials when pushing to europe-west1-docker.pkg.dev.
```bash
# Authenticate Docker with GCP
gcloud auth configure-docker europe-west1-docker.pkg.dev

# Push your image to the registry
docker push europe-west1-docker.pkg.dev/simple-rag-485411/my-rag-repo/simple-rag:v1
```

### 3. Secret Management

Make sure you give your service account **Vertex AI User** and **Secret Manager Secret Accessor** roles.

**Create Pinecone API Key Secret**
We use the `-n` flag to prevent adding a hidden newline (`\n`) to the secret, which would break authentication.
`--data-file=-` means read from standard input (where your key is echoed).
```bash
echo -n "YOUR_PINECONE_KEY" | gcloud secrets create PINECONE_API_KEY --data-file=-
```
> **Note:** Even with the `-n` flag, `\r\n` characters were sometimes read from the secret. Added `.strip()` in [`config.py`](config.py) as a defensive measure to handle any whitespace. Always use `.strip()` when reading secrets to prevent authentication failures.

**Note on Google Credentials**
Locally, we use the `.env` file to specify the service key path and place our JSON file in the root directory. When we initialize our Vertex AI library, it looks for this value and authenticates the service. For GCP, we don't do this. When the Vertex AI library doesn't find the credentials file, it checks the metadata server (which every Cloud Run service has). Since we attached our service account to the service, it returns an auto-rotating token based on that account, which authenticates our app. This approach is better for production because you don't have to store the service key file as a secret (less risk), tokens auto-rotate (better security), and deployment is simplified (no need to mount secret files).

### 4. Deployment

**Deploy to Cloud Run**
Notice we only specify one `--port`. Google's load balancer handles public traffic (HTTPS/443) and forwards it to the container's internal port.
```bash
gcloud run deploy simple-rag-service --image europe-west1-docker.pkg.dev/simple-rag-485411/my-rag-repo/simple-rag:v2 --platform managed --region europe-west1 --allow-unauthenticated --port 8000 --memory 2Gi --cpu 2 --timeout 1000 --service-account="simple-rag-service-account@simple-rag-485411.iam.gserviceaccount.com" --update-secrets="PINECONE_API_KEY=PINECONE_API_KEY:latest"
```

### 5. Maintenance and Backup

**Export Configuration**
Save the "DNA" of your service to a YAML file. If the service is ever deleted, you can recreate it instantly.
```bash
# Create service file
gcloud run services describe simple-rag-service --format export > service.yaml 

# Recreate service from backup
gcloud run services replace service.yaml
```

**Health Check**
Once deployed, verify the service is live: https://simple-rag-service-735784896762.europe-west1.run.app/health
> Note: you can still use the FastAPI docs endpoint to make testing the endpoints easy: https://simple-rag-service-735784896762.europe-west1.run.app/docs#/default/ingest_ingest_post

Try sending a post request to one of the endpoints
```bash
curl -N -X POST https://simple-rag-service-735784896762.europe-west1.run.app/query_stream -H "Content-Type: application/json" -d "{\"query\": \"What is langchain?\"}"
```

---

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