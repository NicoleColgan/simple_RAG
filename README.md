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
