# Production Database Schema

## Overview

The `emp_genai` database uses a normalized, production-ready schema with proper relationships and foreign keys for tracking employee reviews with versioning, chunking, and embeddings.

## Schema Diagram

```
emp_ai schema
├── employee
│   ├── emp_id (PK, String)
│   ├── emp_name
│   ├── department
│   └── date_created
│
├── employee_version (each review session)
│   ├── version_id (PK, Integer, auto-increment)
│   ├── emp_id (FK → employee.emp_id)
│   ├── version (Integer, sequential)
│   ├── transcript_path
│   ├── screenshot_paths (ARRAY)
│   ├── pdf_path
│   ├── status (processing, completed, failed)
│   ├── error_message
│   └── date_created
│
├── employee_version_chunk (chunked text)
│   ├── chunk_id (PK, Integer, auto-increment)
│   ├── version_id (FK → employee_version.version_id)
│   ├── emp_id (FK → employee.emp_id, for filtering)
│   ├── chunk_text (Text)
│   ├── chunk_index (order within version)
│   ├── start_timestamp
│   ├── end_timestamp
│   ├── speaker
│   └── date_created
│
└── employee_version_emb (384-dim vectors)
    ├── emb_id (PK, Integer, auto-increment)
    ├── chunk_id (FK → employee_version_chunk.chunk_id)
    ├── version_id (FK → employee_version.version_id)
    ├── emp_id (FK → employee.emp_id)
    ├── embedding (Vector(384), pgvector)
    └── date_created
```

## Tables

### 1. `employee` Table
Stores unique employees.

**Columns:**
- `emp_id` (String, PK): Unique employee identifier
- `emp_name` (String, nullable): Employee name
- `department` (String, nullable): Department/team
- `date_created` (DateTime): Record creation timestamp

**Indexes:**
- PK on `emp_id`
- Index on `emp_id` for fast lookups

**Relationships:**
- 1-to-many: `versions` (EmployeeVersion records)

### 2. `employee_version` Table
Tracks each review session (version) for an employee.

**Columns:**
- `version_id` (Integer, PK, auto-increment): Unique version identifier
- `emp_id` (String, FK): Foreign key to `employee.emp_id`
- `version` (Integer): Sequential version number per employee
- `transcript_path` (String): Path to transcript file
- `screenshot_paths` (ARRAY(String)): Array of screenshot file paths
- `pdf_path` (String): Generated PDF path
- `status` (String): Pipeline status (`processing`, `chunks_ingested`, `completed`, `failed`)
- `error_message` (Text): Error details if status='failed'
- `date_created` (DateTime): Version creation timestamp

**Indexes:**
- PK on `version_id`
- FK index on `emp_id`
- Unique constraint on `(emp_id, version)`
- Index on `(emp_id, date_created)` for range queries

**Relationships:**
- Many-to-1: Employee (via `emp_id`)
- 1-to-many: `chunks` (EmployeeVersionChunk records)
- 1-to-many: `embeddings` (EmployeeVersionEmb records)

### 3. `employee_version_chunk` Table
Stores text chunks from merged transcript + OCR.

**Columns:**
- `chunk_id` (Integer, PK, auto-increment): Unique chunk identifier
- `version_id` (Integer, FK): Foreign key to `employee_version.version_id`
- `emp_id` (String, FK): Foreign key to `employee.emp_id` (denormalized for filtering)
- `chunk_text` (Text): The actual text content
- `chunk_index` (Integer): Sequential order within version (0, 1, 2, ...)
- `start_timestamp` (String): Transcript timestamp start
- `end_timestamp` (String): Transcript timestamp end
- `speaker` (String): Speaker name/ID from transcript
- `date_created` (DateTime): Creation timestamp

**Indexes:**
- PK on `chunk_id`
- FK index on `version_id`
- FK index on `emp_id`
- Index on `(version_id, chunk_index)` for ordered retrieval

**Relationships:**
- Many-to-1: EmployeeVersion (via `version_id`)
- 1-to-many: `embeddings` (EmployeeVersionEmb records)

### 4. `employee_version_emb` Table
Stores pgvector embeddings (384-dimensional vectors from all-MiniLM-L6-v2).

**Columns:**
- `emb_id` (Integer, PK, auto-increment): Unique embedding identifier
- `chunk_id` (Integer, FK): Foreign key to `employee_version_chunk.chunk_id`
- `version_id` (Integer, FK): Foreign key to `employee_version.version_id`
- `emp_id` (String, FK): Foreign key to `employee.emp_id` (denormalized for filtering)
- `embedding` (Vector(384)): pgvector 384-dimensional cosine vector
- `date_created` (DateTime): Creation timestamp

**Indexes:**
- PK on `emb_id`
- FK index on `chunk_id`
- FK index on `version_id`
- FK index on `emp_id`
- Index on `(emp_id, version_id)` for fast filtering
- **pgvector index** (IVFFlat with cosine distance) for similarity search: `CREATE INDEX idx_emb_vector ON emp_ai.employee_version_emb USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);`

**Relationships:**
- Many-to-1: EmployeeVersionChunk (via `chunk_id`)
- Many-to-1: EmployeeVersion (via `version_id`)

## Key Design Decisions

### 1. **Versioning**
- Each new review creates a new `EmployeeVersion` record
- Allows tracking multiple reviews per employee
- `version` column tracks sequential review numbers (v1, v2, v3, ...)
- Historical data is retained for audit and comparison

### 2. **Chunking Strategy**
- Text is split using RecursiveCharacterTextSplitter
- Each chunk stored in `employee_version_chunk` with metadata
- `chunk_index` preserves order for reconstruction
- Timestamps and speakers link back to source transcript

### 3. **Embedding Storage**
- One embedding per chunk (1-to-1 relationship)
- 384-dimensional vectors from `sentence-transformers/all-MiniLM-L6-v2`
- Cosine distance similarity search via pgvector `<=>` operator
- Denormalized `emp_id` and `version_id` for efficient filtering before vector search

### 4. **Foreign Key Relationships**
- All FKs have ON DELETE CASCADE via ORM cascade
- Deleting a version automatically deletes associated chunks and embeddings
- Deleting an employee removes all versions, chunks, and embeddings

### 5. **Filtering Before Vector Search**
```sql
-- Find top-5 similar chunks for a specific version
SELECT ec.*, ee.embedding <=> query_embedding AS distance
FROM emp_ai.employee_version_chunk ec
JOIN emp_ai.employee_version_emb ee ON ec.chunk_id = ee.chunk_id
WHERE ec.version_id = {version_id} AND ec.emp_id = {emp_id}
ORDER BY ee.embedding <=> query_embedding
LIMIT 5;
```

## Usage Examples

### 1. Create Employee & Version
```python
from app.repositories.vector_repository import VectorRepository

repo = VectorRepository(db)

# Create/get employee
employee = repo.get_or_create_employee(
    emp_id="EMP-001",
    emp_name="John Doe",
    department="Engineering"
)

# Create new version (review session)
version = repo.create_version(
    emp_id="EMP-001",
    transcript_path="data/transcript.txt",
    screenshot_paths=["data/screen1.png", "data/screen2.png"]
)
# Returns: EmployeeVersion(version_id=1, version=1, status='processing')
```

### 2. Ingest Chunks & Embeddings
```python
chunks = ["chunk text 1", "chunk text 2", "chunk text 3"]

chunk_rows, emb_rows = repo.insert_chunks_and_embeddings(
    version_id=version.version_id,
    emp_id="EMP-001",
    chunks=chunks,
    metadata={}  # optional per-chunk metadata
)
# Returns: 
#   chunk_rows: [EmployeeVersionChunk, EmployeeVersionChunk, ...]
#   emb_rows: [EmployeeVersionEmb, EmployeeVersionEmb, ...]
```

### 3. Search Similar Chunks
```python
# Search within a specific version
results = repo.similarity_search(
    query="employee strengths",
    emp_id="EMP-001",
    version_id=1,
    top_k=5
)
# Returns: [(chunk, embedding, distance), ...]

# Search across all versions for employee
results = repo.similarity_search(
    query="employee strengths",
    emp_id="EMP-001",
    version_id=None,  # all versions
    top_k=5
)
```

### 4. Retrieve All Chunks
```python
# Get all chunks for a version
chunks = repo.get_chunks_for_version(version_id=1, emp_id="EMP-001")

# Get count
count = repo.count_chunks_in_version(version_id=1, emp_id="EMP-001")
```

### 5. Use as LangChain Retriever
```python
# Build retriever for RAG
retriever = repo.as_retriever(
    emp_id="EMP-001",
    version_id=1,
    top_k=5
)

# Use with LangChain
from langchain.chains import RetrievalQA
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff"
)

answer = qa_chain.run("What are the employee's key strengths?")
```

### 6. Update Version Status
```python
# Mark version as completed
repo.update_version_status(
    version_id=1,
    status="completed"
)

# Mark version as failed with error
repo.update_version_status(
    version_id=1,
    status="failed",
    error_message="OCR failed: Image quality too low"
)
```

## API Endpoints

### POST `/api/v1/run-employee-review`
Run full pipeline: OCR → Transcript → PDF → Chunk → Embed → RAG → Generate

**Request:**
```json
{
  "emp_id": "EMP-001",
  "emp_name": "John Doe",
  "department": "Engineering",
  "screenshot_paths": ["data/screen1.png"],
  "transcript_path": "data/transcript.txt"
}
```

**Response:**
```json
{
  "emp_id": "EMP-001",
  "version_id": 1,
  "version": 1,
  "answers": {
    "Q1": {
      "question": "What are key strengths?",
      "sub_answers": [...],
      "combined_answer": "..."
    }
  },
  "docx_path": "output/EMP-001_final_answer.docx"
}
```

### GET `/api/v1/employee/{emp_id}/versions`
List all versions for an employee

### GET `/api/v1/employee/{emp_id}/version/{version_id}/chunks`
Get chunks for a specific version (paginated)

### POST `/api/v1/employee/{emp_id}/version/{version_id}/search`
Search for similar chunks using pgvector

### GET `/api/v1/download/{emp_id}`
Download latest docx result

### GET `/api/v1/download/{emp_id}/version/{version_id}`
Download docx for specific version

## Performance Considerations

### Vector Similarity Search
- pgvector IVFFlat index recommended for large datasets (>10K vectors)
- Index parameters: `lists = sqrt(total_vectors)`, e.g., 100 for ~10K vectors
- Cosine distance (`<=>` operator) is optimal for embeddings

### Query Optimization
1. **Filter by version first** before vector search
```sql
-- GOOD: Filter by version, then search
SELECT ... WHERE version_id = ? ORDER BY embedding <=> ? LIMIT 5;

-- AVOID: Vector search across all employees
SELECT ... ORDER BY embedding <=> ? LIMIT 5;
```

2. **Index Strategy**
```sql
-- Composite index for filtering + ordering
CREATE INDEX idx_version_emb ON emp_ai.employee_version_emb 
  (version_id, emp_id);

-- Vector index for similarity
CREATE INDEX idx_vector ON emp_ai.employee_version_emb 
  USING ivfflat (embedding vector_cosine_ops);
```

3. **Pagination**
```python
# Use offset/limit for chunks
chunks = db.query(EmployeeVersionChunk).filter(...).offset(0).limit(10)
```

## Migration & Initialization

### Automatic (on app startup)
```python
# main.py calls this in lifespan startup
from app.config.database import init_db
init_db()
```

### Manual
```python
from app.config.database import init_db, drop_all_tables
from sqlalchemy import text
from app.config.database import engine

# Initialize
init_db()

# Drop all (use with caution)
drop_all_tables()

# Custom: Create IVFFlat vector index
with engine.begin() as conn:
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_emb_vector 
        ON emp_ai.employee_version_emb 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100);
    """))
```

## SQL Examples

### Count chunks per version
```sql
SELECT version_id, emp_id, COUNT(*) as chunk_count
FROM emp_ai.employee_version_chunk
GROUP BY version_id, emp_id
ORDER BY version_id DESC;
```

### Find versions by status
```sql
SELECT * FROM emp_ai.employee_version
WHERE status = 'completed'
ORDER BY date_created DESC;
```

### Get latest version for employee
```sql
SELECT * FROM emp_ai.employee_version
WHERE emp_id = 'EMP-001'
ORDER BY version DESC
LIMIT 1;
```

### Find failed versions with error messages
```sql
SELECT version_id, emp_id, error_message, date_created
FROM emp_ai.employee_version
WHERE status = 'failed'
ORDER BY date_created DESC;
```

### Vector similarity search (raw SQL)
```sql
SELECT c.chunk_id, c.chunk_text, e.embedding <=> 
  (SELECT embedding FROM pgvector.encode('[...384 dims...]', 'float32'))
  AS distance
FROM emp_ai.employee_version_chunk c
JOIN emp_ai.employee_version_emb e ON c.chunk_id = e.chunk_id
WHERE c.version_id = 1 AND c.emp_id = 'EMP-001'
ORDER BY distance
LIMIT 5;
```

## Troubleshooting

### Q: pgvector extension not found
**Solution:** Enable it manually:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Q: Schema `emp_ai` doesn't exist
**Solution:** Created automatically by `init_db()`, or manually:
```sql
CREATE SCHEMA IF NOT EXISTS emp_ai;
```

### Q: Slow vector searches
**Solution:** Create IVFFlat index:
```sql
CREATE INDEX idx_vector ON emp_ai.employee_version_emb 
  USING ivfflat (embedding vector_cosine_ops) 
  WITH (lists = 100);
```

### Q: Foreign key violations
**Solution:** Check cascade delete settings in ORM relationship definitions. All relationships have `cascade="all, delete-orphan"` to auto-clean orphaned records.
