# Quick Reference: Production Schema Overview

## Before → After

### Schema Structure

**BEFORE (Flat):**
```
EmployeeTable
├── emp_id (PK)
├── date_created (PK)
├── start_timestamp (PK)
├── chunk
├── emb
└── ... metadata scattered
```
❌ No versioning
❌ No relationships
❌ No status tracking

**AFTER (Normalized):**
```
Employee
  └── EmployeeVersion (1-to-many)
      ├── EmployeeVersionChunk (1-to-many)
      │   └── EmployeeVersionEmb (1-to-1)
      └── EmployeeVersionEmb (1-to-many)
```
✅ Versioning built-in
✅ Proper relationships
✅ Status tracking
✅ Employee metadata

---

## ORM Models: Quick Reference

### Employee
```python
Employee(
    emp_id: str,           # "EMP-001"
    emp_name: str,         # "John Doe"
    department: str,       # "Engineering"
    date_created: datetime,
    versions: List[EmployeeVersion]  # relationship
)
```

### EmployeeVersion
```python
EmployeeVersion(
    version_id: int,           # 1, 2, 3... (auto-increment)
    emp_id: str,               # "EMP-001"
    version: int,              # 1, 2, 3... (per employee)
    status: str,               # "processing" → "completed" or "failed"
    transcript_path: str,
    screenshot_paths: List[str],
    pdf_path: str,
    error_message: str,        # if status="failed"
    date_created: datetime,
    chunks: List[EmployeeVersionChunk],  # relationship
    embeddings: List[EmployeeVersionEmb] # relationship
)
```

### EmployeeVersionChunk
```python
EmployeeVersionChunk(
    chunk_id: int,             # 1, 2, 3... (auto-increment)
    version_id: int,           # FK to EmployeeVersion
    emp_id: str,               # FK to Employee
    chunk_text: str,           # "The text content..."
    chunk_index: int,          # 0, 1, 2... (order)
    start_timestamp: str,      # "00:15:23"
    end_timestamp: str,        # "00:15:45"
    speaker: str,              # "Manager" or speaker name
    date_created: datetime,
    embeddings: List[EmployeeVersionEmb]  # relationship
)
```

### EmployeeVersionEmb
```python
EmployeeVersionEmb(
    emb_id: int,               # 1, 2, 3... (auto-increment)
    chunk_id: int,             # FK to EmployeeVersionChunk
    version_id: int,           # FK to EmployeeVersion
    emp_id: str,               # FK to Employee
    embedding: Vector(384),    # pgvector [0.1, 0.2, ...]
    date_created: datetime
)
```

---

## Repository Methods: Quick Reference

### Employee Management
```python
# Get or create
employee = repo.get_or_create_employee(
    emp_id="EMP-001",
    emp_name="John Doe",
    department="Engineering"
)
```

### Version Management
```python
# Create new review session
version = repo.create_version(
    emp_id="EMP-001",
    transcript_path="data/transcript.txt",
    screenshot_paths=["data/screen1.png"]
)
# Returns: EmployeeVersion(version_id=1, version=1, status="processing")

# Update status
repo.update_version_status(
    version_id=version.version_id,
    status="completed"  # or "failed"
)
```

### Data Ingestion
```python
# Embed and ingest chunks
chunks_rows, emb_rows = repo.insert_chunks_and_embeddings(
    version_id=version.version_id,
    emp_id="EMP-001",
    chunks=["chunk 1 text", "chunk 2 text", ...]
)
# Automatically generates 384-dim embeddings
# Stores chunks and embeddings with relationships
```

### Data Retrieval
```python
# Search similar chunks
results = repo.similarity_search(
    query="employee strengths",
    emp_id="EMP-001",
    version_id=1,  # None for all versions
    top_k=5
)
# Returns: [(chunk, embedding, distance), ...]

# Get all chunks for a version
chunks = repo.get_chunks_for_version(
    version_id=1,
    emp_id="EMP-001"
)

# Count chunks
count = repo.count_chunks_in_version(
    version_id=1,
    emp_id="EMP-001"
)
```

### LangChain Integration
```python
# Get LangChain-compatible retriever
retriever = repo.as_retriever(
    emp_id="EMP-001",
    version_id=1,
    top_k=5
)

# Use with RetrievalQA
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff"
)
answer = qa_chain.run("What are strengths?")
```

### Cleanup
```python
# Delete specific version
repo.delete_version(version_id=1)

# Delete all data for employee
repo.delete_employee(emp_id="EMP-001")
```

---

## API Endpoints: Quick Reference

### Run Full Pipeline
```bash
POST /api/v1/run-employee-review
Content-Type: application/json

{
  "emp_id": "EMP-001",
  "emp_name": "John Doe",
  "department": "Engineering",
  "screenshot_paths": ["data/screen1.png"],
  "transcript_path": "data/transcript.txt"
}

Response (201):
{
  "emp_id": "EMP-001",
  "version_id": 1,
  "version": 1,
  "answers": {
    "Q1": {...},
    "Q2": {...},
    ...
  },
  "docx_path": "output/EMP-001_final_answer.docx"
}
```

### List All Versions for Employee
```bash
GET /api/v1/employee/{emp_id}/versions

Response:
{
  "emp_id": "EMP-001",
  "emp_name": "John Doe",
  "department": "Engineering",
  "total_versions": 3,
  "versions": [
    {
      "version_id": 3,
      "version": 3,
      "status": "completed",
      "date_created": "2024-11-21T10:30:00",
      "chunk_count": 145,
      "error_message": null
    },
    ...
  ]
}
```

### Get Chunks for Version (Paginated)
```bash
GET /api/v1/employee/{emp_id}/version/{version_id}/chunks?limit=10&offset=0

Response:
{
  "emp_id": "EMP-001",
  "version_id": 1,
  "total_chunks": 145,
  "limit": 10,
  "offset": 0,
  "chunks": [
    {
      "chunk_id": 1,
      "chunk_index": 0,
      "text": "Employee demonstrated...",
      "full_text": "...",
      "speaker": "Manager",
      "start_timestamp": "00:15:23",
      "end_timestamp": "00:15:45"
    },
    ...
  ]
}
```

### Vector Similarity Search
```bash
POST /api/v1/employee/{emp_id}/version/{version_id}/search?query=strengths&top_k=5

Response:
{
  "emp_id": "EMP-001",
  "version_id": 1,
  "query": "strengths",
  "results": [
    {
      "chunk_id": 5,
      "chunk_index": 4,
      "text": "Strong communication...",
      "full_text": "...",
      "similarity_distance": 0.145,  # lower = more similar
      "speaker": "Manager",
      "start_timestamp": "00:15:30"
    },
    ...
  ]
}
```

### Download Results
```bash
# Latest version
GET /api/v1/download/{emp_id}

# Specific version
GET /api/v1/download/{emp_id}/version/{version_id}

Response: (Word document file)
```

---

## Database Workflow

### Typical Session

```python
from app.repositories.vector_repository import VectorRepository
from app.config.database import SessionLocal

db = SessionLocal()
repo = VectorRepository(db)

# Step 1: Create/Get Employee
employee = repo.get_or_create_employee(
    emp_id="EMP-001",
    emp_name="John Doe",
    department="Engineering"
)

# Step 2: Create Version for Review Session
version = repo.create_version(
    emp_id="EMP-001",
    transcript_path="data/transcript.txt",
    screenshot_paths=["data/screen1.png", "data/screen2.png"]
)

# Step 3: Process Data (OCR, chunking, etc.)
chunks = ["chunk1", "chunk2", ...]

# Step 4: Ingest Chunks & Embeddings
chunk_rows, emb_rows = repo.insert_chunks_and_embeddings(
    version_id=version.version_id,
    emp_id="EMP-001",
    chunks=chunks
)

# Step 5: Mark chunks ingested
repo.update_version_status(
    version_id=version.version_id,
    status="chunks_ingested"
)

# Step 6: Build Retriever for RAG
retriever = repo.as_retriever(
    emp_id="EMP-001",
    version_id=version.version_id,
    top_k=5
)

# Step 7: Use with LLM/RAG (in your code)
# ... LLM queries retriever for context ...

# Step 8: Mark as completed
repo.update_version_status(
    version_id=version.version_id,
    status="completed"
)

db.close()
```

---

## Pipeline Status States

```
┌─────────────┐
│  processing │  ← New version created
└──────┬──────┘
       │
       ↓
┌──────────────────┐
│ chunks_ingested  │  ← Text chunked and embedded
└──────┬───────────┘
       │
       ├─→ ✅ completed  (LLM generated answers)
       │
       └─→ ❌ failed     (Error during pipeline)
```

---

## Common Queries

### Count Data
```sql
-- Employees with multiple versions
SELECT emp_id, COUNT(*) as version_count
FROM emp_ai.employee_version
GROUP BY emp_id;

-- Chunks per version
SELECT version_id, COUNT(*) as chunk_count
FROM emp_ai.employee_version_chunk
GROUP BY version_id;

-- Embeddings generated
SELECT COUNT(*) FROM emp_ai.employee_version_emb;
```

### Find Failed Reviews
```sql
SELECT version_id, emp_id, error_message, date_created
FROM emp_ai.employee_version
WHERE status = 'failed'
ORDER BY date_created DESC;
```

### Get Latest Version
```sql
SELECT * FROM emp_ai.employee_version
WHERE emp_id = 'EMP-001'
ORDER BY version DESC
LIMIT 1;
```

### Vector Search (Raw SQL)
```sql
SELECT c.chunk_id, c.chunk_text, e.embedding <=> query_vector AS distance
FROM emp_ai.employee_version_chunk c
JOIN emp_ai.employee_version_emb e ON c.chunk_id = e.chunk_id
WHERE c.version_id = 1 AND c.emp_id = 'EMP-001'
ORDER BY distance
LIMIT 5;
```

---

## Setup Checklist

- [ ] PostgreSQL 14+ installed
- [ ] pgvector extension installed
- [ ] Create emp_genai database
- [ ] Python 3.12+ with venv
- [ ] pip install -r requirements.txt
- [ ] Set DB_URL in .env
- [ ] Download GGUF model file
- [ ] python app/main.py (auto-init DB)
- [ ] Test: curl http://localhost:8000/health
- [ ] Run sample review request
- [ ] Verify data in database
- [ ] Deploy to production

---

## Performance Tips

1. **Vector Search:**
   - Filter by version_id first
   - Use IVFFlat index for large datasets
   - Cosine distance is optimal for embeddings

2. **Chunking:**
   - Larger chunks (1000 tokens) = fewer vectors, faster search
   - Smaller chunks (100 tokens) = more precise but slower

3. **Batching:**
   - Always use insert_chunks_and_embeddings() for batch ops
   - Avoid inserting chunks one-at-a-time

4. **Queries:**
   - Always filter by version before vector search
   - Use pagination for large result sets
   - Use lazy loading for relationships

---

## Support & Resources

- **Schema Details:** DATABASE_SCHEMA.md
- **Setup Guide:** PRODUCTION_SETUP.md
- **Migration:** MIGRATION_GUIDE.md
- **Full Summary:** IMPLEMENTATION_SUMMARY.md
- **API Docs:** http://localhost:8000/docs (Swagger UI)

---

**Version:** 1.0.0 (Production Ready)
**Last Updated:** 2024-11-21
