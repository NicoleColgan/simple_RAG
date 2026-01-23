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
