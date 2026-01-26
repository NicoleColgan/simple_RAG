# Plan

## Primary focus
* RAG project on GCP
* Use Vertex AI, Pinecone, FastAPI
* Deploy on cloud run
* Expose clean rest APIs
* Implement agent orchestration

## Phase 1
**RAG service on Vertex AI**

**Tech Stack**
* Python
* FastAPI (async)
* Vertex AI (Gemini or text-embedding model)
* Pinecone (managed, fast to wire)
* GCS for docs

**Capeabilities**
* Upload PDFs
* Chunk and embed
* Store Vectors
* Query with metadata filtering
* Return grounded answers

**Expose Endpoints**
```http
POST /injest
POST /query
GET /health
```

## Phase 2: Agentic orchestration
Turning project into Agent tool

**Agent flow**
* Planner agent decides:
    - "Do I need docs?"
    - "Which tool?"
* Executor agent:
    - Calls RAG
    - Calls external APIs
* Verifier agent:
    - Checks confidence
    - Enforces rules

Use:
* LangGraph (best for explicit state machines)

## Phase 4: Cloud nmative and enterprise polish
**GCP deployment**
* Cloud run (API)
* Cloud run (frontend - later)
* Pub/Sub (async agent steps)
* Secret manager

**Observability**
* Structured logs per agent step
* Request IDs
* Latency metrics

# Database
* Pinecone: fast setup, clean api, enterprise friendly

# Archtecture
```
Client
    -> FastAPI (Cloud Run)
        -> Agent Orchestrator (LangGraph)
            -> RAG tool (Vertex + Pinecone)
            -> External APIs
        -> Pub/Sub (async tasks)
```

### Courses & Independent research
1. Vertex AI Essentials (Google cloud - vvertex ai essentials): models, endpoints, auth, cost control
2. LangGraph course
3. Fast API short refresher
4. Python advanced refresher
## Chunking Strategy (RAG)

The goal of chunking is to improve retrieval quality.

You want chunks that:
- Are semantically coherent
- Fit within embedding and prompt limits
- Retrieve enough context while minimising noise
- Don’t get “orphaned” from their meaning

---

### Default (good for ~80% of RAG apps)

```python
RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
```
### Why this works

- Overlap only applies when long sentences must be split
- ~500 characters ≈ a “thought-sized” chunk
- Cheap, predictable, and robust

✅ **Use this unless you have a strong reason not to**

---

### When to increase `chunk_size`

Increase chunk size if:
- Documents are concept-heavy (tutorials, specs, guides)
- Answers are almost correct but missing key context
- Retrieved chunks feel incomplete

---

### When to decrease `chunk_size`

Decrease chunk size if:
- Documents contain many unrelated ideas
- Retrieval pulls in irrelevant context
- You’re embedding logs, FAQs, or short Q&A-style content

---

### How to choose `chunk_overlap`

**Rule of thumb:**

> **Overlap ≈ 10–20% of `chunk_size`**

This preserves sentence continuity without excessive redundancy.

---

### Choose strategy by content type

#### 📄 Plain text / articles
```python
RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
```
### Choose strategy by content type

#### 📘 PDFs / manuals
* Text extraction is often messy
* Paragraph boundaries are unreliable
```python
RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)
```

#### 💬 FAQs / short answers
```python
RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=30
)
```

#### 💻 Code
❌ Do NOT use character-based splitters

Instead, use:
* Function-level splitting
* File-level or semantic splitting
* Chunking code by characters destroys structure and meaning

---

### Chunk Metadata & ID Strategy

Each chunk is stored with the following metadata:

```python
{
    "id": "<deterministic-hash>",
    "data": "<chunk-text>",
    "file_name": "<source-filename>",
    "content_type": "<mime-type>"
}
```

#### Why Deterministic Hash IDs?

**Hash-based ID generation:**
```python
hashlib.sha256(f"{file_name}-{chunk}".encode("utf-8")).hexdigest()
```

**Advantages over UUID:**
- ✅ **Deduplication**: Same content = same ID, making it easy to detect and skip duplicate chunks
- ✅ **Deterministic**: Re-ingesting the same file produces identical IDs
- ✅ **Idempotent**: Safe to re-run ingestion without creating duplicates in the vector DB
- ✅ **Content-addressable**: ID represents the actual content, not just a random identifier

**UUID approach (NOT used):**
```python
str(uuid.uuid4())  # Random ID every time
```
- ❌ **No deduplication**: Same chunk ingested twice = two different IDs
- ❌ **Database bloat**: Duplicate content creates redundant vectors
- ❌ **Wasted storage**: Same embeddings stored multiple times

**Use case:**
If you upload the same document twice, the hash-based approach allows your vector DB to recognize and skip duplicates, saving storage and preventing retrieval confusion.

---

#### Learnings
1. **FastAPI File Uploads**
    * `UploadFile`
        * FastAPIs class for uploaded files
        * Provides useful attributes and methods like `read()`, `.filename`, `content_type`
        * Use this when processing file uploads for ingestion
    * `File(...)`
        * Instruction to FastAPI to extract files from `multipart/form-data` rewust 
        * `(...)` (ellipsis) means the fild is required
        * Works together with `UploadFile` to inject actual files into the endpoint
2. **Response Model with Pydantic**
    * `IngestResponse` example:
        * Fields must be provided when returning an instance (no defaults)
        * FastAPI uses this to validate the output, serialise it JSON, and generate automatic API docs
        * Optional fields can be defined as `=None`
3. **Logging Config**
    * `level` = minimum severity to log (DEBUG < INFO < WARNING < ERROR < CRITICAL)
    * `format` defines how the logs look with placeholders automatically filled by logger
4. **RecursiveCharacterTextSplitter**
    * Tries to split text while preserving logical structure.
    * Since text is usually organised hierarchically (paragraphs → lines → spaces → characters),
      it attempts to split using these separators in that order.
    * It prefers to keep larger units (e.g. paragraphs) intact, and only moves to smaller
      separators if a chunk exceeds the configured `chunk_size`.
    * If a chunk is too large at a given separator level, only that chunk is recursively
      re-processed using the next separator.

    * Example behaviour (using `chunk_size = 100`):
        * The splitter first tries to split on `"\n\n"` (paragraphs).
          If this produces chunks that are all < 100 characters, those chunks are accepted.
        * If splitting on `"\n\n"` produces a chunk that is still too large, the splitter
          targets only that chunk and retries using the next separator (`"\n"`).
        * In the example, a multi-line paragraph is split on `"\n"` into two chunks, both < 100,
          so the split succeeds at that level.
        * After a successful split, the splitter may merge adjacent chunks **if the combined
          length stays under `chunk_size`**.
        * When encountering a long sentence with no line breaks, the splitter cannot use `"\n"`,
          so it falls back to splitting on `" "` (spaces).
        * If a chunk still cannot be split (e.g. a very long word), the final fallback is
          character-level splitting.

    * **Overlap behaviour**
        * `chunk_overlap` is only applied when a chunk must be forcibly split because it
          still exceeds `chunk_size` after separator-based splitting.
        * In practice, this means overlap usually appears only for word-level or
          character-level splits, not for paragraph or line splits.


---

## Google Cloud Storage Setup

### Why Use GCS?
When users upload files via your API, you need persistent storage to access them later. The vector database only stores embeddings for similarity search - you still need the original documents to show users where answers came from, prove what data generated responses (compliance/audit), and enable features like file downloads.

Additionally, storing source files in GCS allows you to reprocess your entire corpus when you improve chunking strategies or switch embedding models, debug issues by comparing chunks to original documents, and recover from disasters if your vector DB crashes. While technically optional, GCS provides critical benefits for production RAG systems at minimal cost (~€0.02/GB/month)

### Project Configuration
- **Project ID**: `simple-rag-485411`
- **Service Account**: `simple-rag-service-account@simple-rag-485411.iam.gserviceaccount.com`
- **Region**: `europe-west1` (Belgium - closest to Ireland)
- **Bucket Name**: `simple-rag-bucket`

---

### Setup Steps

#### 1. Create GCP Project
In GCP, everything lives in a **project** - a container for all your resources (buckets, VMs, APIs, etc.).

1. Go to https://console.cloud.google.com/
2. Create a new project and name it `simple-RAG`
3. Note the auto-generated project ID: `simple-rag-485411`
4. Always ensure this project is selected in the top dropdown when working

#### 2. Enable Cloud Storage API
Your project needs permission to use Google Cloud Storage:

1. Go to **APIs & Services** → **Enable APIs and Services**
2. Search for "Cloud Storage API"
3. Click **Enable**

#### 3. Create Service Account (for programmatic access)
Your Python code needs credentials to access GCS securely:

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Name: `simple-rag-service-account`
4. Grant role: **Storage Object Admin** (allows upload/download/delete objects)
5. Click **Create and Continue** → **Done**
6. Click on the service account → **Keys** tab → **Add Key** → **Create New Key**
7. Choose **JSON** format → Download the key file
8. Save it as `rag-service-account.json` in your project root

**🚨 SECURITY WARNING:**
- ❌ **NEVER commit `rag-service-account.json` to GitHub** - it contains private credentials
- Add to `.gitignore` immediately:
  ```gitignore
  rag-service-account.json
  *.json
  ```
- In production, use **Secret Manager** or environment variables instead of local JSON files

#### 4. Create Storage Bucket
Buckets are where files are stored. 

**Via Console (Recommended for first time)**
1. Go to **Cloud Storage** → **Buckets** → **Create Bucket**
2. **Name**: `simple-rag-bucket` (include project ID for uniqueness)
3. **Location type**: Region
4. **Region**: `europe-west1`
5. **Storage class**: Standard (frequent access)
6. **Access control**: Uniform (IAM only)
7. **Public access**: Enforce prevention (keep private)
8. **Soft delete**: Use default (7 days)
9. **Object versioning**: Disabled
10. Click **Create**

#### 5. Install Google Cloud Storage Client Library
```bash
pip install google-cloud-storage
```

---

### Code Implementation

#### Authentication Setup
```python
import os
from google.cloud import storage

# Point to your service account key (local development only)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "rag-service-account.json"

# Initialize GCS client
client = storage.Client()
bucket_name = "simple-rag-bucket"
bucket = client.bucket(bucket_name)
```

#### Uploading Files
```python
# Upload file to GCS
blob = bucket.blob(file_name)  # Create a blob reference
blob.upload_from_string(content)  # Upload bytes
gcs_uri = f"gs://{bucket_name}/{file_name}"  # GCS path
```

**What is a Blob?**
- **Blob** = Binary Large Object = GCS term for a file/object stored in a bucket
- Think of it as: **Bucket = Folder**, **Blob = File**
- `bucket.blob(file_name)` creates a reference to a file location (doesn't upload yet)
- `blob.upload_from_string(content)` actually uploads the bytes to GCS

**GCS URI Format:**
- Format: `gs://bucket-name/file-name`
- Example: `gs://simple-rag-485411-documents/document.pdf`
- This URI is stored in chunk metadata for traceability