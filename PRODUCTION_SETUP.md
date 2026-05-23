# Production Setup Guide

## Prerequisites

- **Python**: 3.12+
- **PostgreSQL**: 14+ with pgvector extension
- **Operating System**: Windows, macOS, or Linux
- **Disk Space**: At least 2GB (for GGUF models)
- **Memory**: 8GB RAM recommended

## Step 1: Database Setup

### 1.1 PostgreSQL Installation & Configuration

**Windows (using PostgreSQL installer):**
```powershell
# Download and install from: https://www.postgresql.org/download/windows/
# During installation, note your password and port (usually 5432)

# After installation, open PowerShell as Administrator and verify:
psql --version
```

**macOS (using Homebrew):**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 1.2 Create Database & Schema

```powershell
# Connect to PostgreSQL (Windows)
psql -U postgres

# Or on macOS/Linux:
psql -U postgres
```

In the PostgreSQL prompt:
```sql
-- Create database
CREATE DATABASE emp_genai;

-- Connect to the database
\c emp_genai

-- Create extension for pgvector (auto-created by init_db() on startup, but you can also do it manually)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema (auto-created by init_db() on startup)
CREATE SCHEMA IF NOT EXISTS emp_ai;

-- Verify
\dt emp_ai.*
```

Exit with `\q`

## Step 2: Python Environment Setup

### 2.1 Enable Windows Long Path Support (Windows Only)

**CRITICAL**: Without this step, `pip install -r requirements.txt` will fail due to nested paths in `llama-cpp-python`.

```powershell
# Open Group Policy Editor (Windows only)
# Press Win+R, type: gpedit.msc

# Navigate to:
# Computer Configuration 
#   > Administrative Templates 
#   > System 
#   > Filesystem

# Find and enable: "Enable Win32 long paths"

# Restart your computer
```

Alternatively, via PowerShell (as Administrator):
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### 2.2 Create Virtual Environment

```powershell
# Navigate to project directory
cd C:\Users\pstan\emp_rag

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source .venv/bin/activate
```

### 2.3 Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installations
pip list | grep -E "fastapi|langchain|pgvector|sqlalchemy|llama-cpp-python"
```

## Step 3: Configuration

### 3.1 Create .env File

Create a `.env` file in the project root:

```bash
# PostgreSQL connection
DB_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/emp_genai

# LLM Configuration
MODEL_PATH=models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
LLM_THREADS=4

# Embedding Model
EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Document Templates
TEMPLATE_PATH=templates/template_answer.docx
OUTPUT_DIR=output
```

### 3.2 Update Connection String

Replace `YOUR_PASSWORD` with your PostgreSQL password from Step 1.

## Step 4: Download GGUF Models

The LLM requires a pre-quantized model file in GGUF format.

### Options:

**Option 1: TinyLlama (RECOMMENDED for testing)**
```bash
# Fast, 1.1B parameters, ~700MB
pip install huggingface-hub
huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF \
  --include "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" \
  --local-dir models/
```

**Option 2: Phi-2 (Better quality)**
```bash
# Better performance, 2.7B parameters, ~1.6GB
huggingface-cli download TheBloke/phi-2-GGUF \
  --include "phi-2.Q4_K_M.gguf" \
  --local-dir models/
```

**Option 3: Mistral 7B (Best quality)**
```bash
# Best output quality, 7B parameters, ~4GB
huggingface-cli download TheBloke/Mistral-7B-Instruct-v0.1-GGUF \
  --include "mistral-7b-instruct-v0.1.Q4_K_M.gguf" \
  --local-dir models/
```

Verify:
```bash
ls -la models/*.gguf
```

## Step 5: Database Initialization

### Option 1: Automatic (Recommended)

The database will auto-initialize on first app startup:

```bash
python app/main.py
# Wait for log: "✓ Database initialized successfully"
```

### Option 2: Manual

```python
python -c "from app.config.database import init_db; init_db()"
```

Verify tables were created:
```sql
psql -U postgres -d emp_genai -c "\dt emp_ai.*"
```

Expected output:
```
             List of relations
 Schema |            Name
--------+---------------------------
 emp_ai | employee
 emp_ai | employee_version
 emp_ai | employee_version_chunk
 emp_ai | employee_version_emb
(4 rows)
```

## Step 6: Run Application

### Production Start

```bash
# Activate venv (if not already active)
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\Activate.ps1  # Windows

# Start API server
python app/main.py
```

Expected startup logs:
```
INFO | 2024-11-21 10:30:00,123 | app.config.database — Enabling pgvector extension...
INFO | 2024-11-21 10:30:00,234 | app.config.database — Creating emp_ai schema...
INFO | 2024-11-21 10:30:00,345 | app.config.database — Creating tables in emp_ai schema...
INFO | 2024-11-21 10:30:00,456 | app.config.database — Database initialized successfully
INFO | 2024-11-21 10:30:00,567 | app.main — emp-genai API starting up …
INFO | 2024-11-21 10:30:02,789 | uvicorn.server — Application startup complete [PID 12345]
```

### Verify Health

```bash
curl http://localhost:8000/health
# Response: {"status":"ok","service":"emp-genai"}
```

### Access API Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Step 7: Test Pipeline

### Sample Request

Create `test_request.json`:
```json
{
  "emp_id": "EMP-TEST-001",
  "emp_name": "Jane Doe",
  "department": "Product",
  "screenshot_paths": [
    "data/screen1.png",
    "data/screen2.png"
  ],
  "transcript_path": "data/transcript.txt"
}
```

Run:
```bash
curl -X POST http://localhost:8000/api/v1/run-employee-review \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

### Expected Response

```json
{
  "emp_id": "EMP-TEST-001",
  "version_id": 1,
  "version": 1,
  "answers": {
    "Q1": {
      "question": "What are the employee's key strengths?",
      "sub_answers": [...],
      "combined_answer": "..."
    },
    "Q2": {...},
    ...
  },
  "docx_path": "output/EMP-TEST-001_final_answer.docx"
}
```

### Retrieve Data

```bash
# List all versions for employee
curl http://localhost:8000/api/v1/employee/EMP-TEST-001/versions

# Search similar chunks
curl -X POST "http://localhost:8000/api/v1/employee/EMP-TEST-001/version/1/search?query=strengths&top_k=5"

# Download result
curl http://localhost:8000/api/v1/download/EMP-TEST-001 \
  --output result.docx
```

## Step 8: Troubleshooting

### Issue: "psql: command not found"
**Solution**: PostgreSQL not in PATH. Add to system PATH or use full path.

### Issue: "psycopg2 connection refused"
**Solution**: 
- Verify PostgreSQL is running: `pg_isready -h localhost -p 5432`
- Check DB_URL in .env file
- Verify password is correct

### Issue: "pgvector extension not found"
**Solution**: 
- Install pgvector: `pip install pgvector`
- Enable in PostgreSQL: `CREATE EXTENSION vector;`

### Issue: "Long paths error" (Windows)
**Solution**: 
- Enable Windows Long Path support (Step 2.1)
- Or use pre-compiled binary: `pip install llama-cpp-python --only-binary :all:`

### Issue: "out of memory" or "killed"
**Solution**:
- Use smaller model (TinyLlama instead of Mistral)
- Reduce chunk size in `app/services/chunk_service.py`
- Reduce `top_k` in retriever queries

### Issue: "No module named app"
**Solution**: 
- Run from project root directory
- Activate virtual environment

## Step 9: Production Deployment

### Environment Variables
Store all secrets in `.env` (never commit to git):
```bash
# .env (example)
DB_URL=postgresql://prod_user:secure_password@prod_host:5432/emp_genai
MODEL_PATH=/models/mistral-7b.gguf
LLM_THREADS=8
```

### Systemd Service (Linux)

Create `/etc/systemd/system/emp-genai.service`:
```ini
[Unit]
Description=emp-genai Employee Review API
After=network.target postgresql.service

[Service]
Type=simple
User=app-user
WorkingDirectory=/opt/emp-genai
Environment="PATH=/opt/emp-genai/.venv/bin"
ExecStart=/opt/emp-genai/.venv/bin/python /opt/emp-genai/app/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable emp-genai
sudo systemctl start emp-genai
sudo systemctl status emp-genai
```

### Reverse Proxy (nginx)

```nginx
upstream emp_genai {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://emp_genai;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Download model
RUN huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF \
    --include "*.gguf" --local-dir models/

EXPOSE 8000

CMD ["python", "app/main.py"]
```

Build and run:
```bash
docker build -t emp-genai .
docker run -p 8000:8000 --env-file .env emp-genai
```

## Monitoring

### Logs

```bash
# Real-time logs
tail -f /var/log/emp-genai/app.log

# Check for errors
grep ERROR /var/log/emp-genai/app.log
```

### Database Health

```sql
-- Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'emp_ai'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check row counts
SELECT 
  'employee' as table_name, COUNT(*) FROM emp_ai.employee
UNION ALL SELECT 
  'employee_version', COUNT(*) FROM emp_ai.employee_version
UNION ALL SELECT 
  'employee_version_chunk', COUNT(*) FROM emp_ai.employee_version_chunk
UNION ALL SELECT 
  'employee_version_emb', COUNT(*) FROM emp_ai.employee_version_emb;
```

### Performance Metrics

```bash
# Watch query performance
watch -n 1 'psql -d emp_genai -c "SELECT COUNT(*) FROM emp_ai.employee_version_emb;"'
```

## Backup & Restore

### Backup

```bash
# Full database backup
pg_dump -U postgres emp_genai > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup with compression
pg_dump -U postgres -Fc emp_genai > backup_$(date +%Y%m%d_%H%M%S).dump
```

### Restore

```bash
# From SQL file
psql -U postgres emp_genai < backup_20240101_000000.sql

# From compressed dump
pg_restore -U postgres -d emp_genai backup_20240101_000000.dump
```

## Next Steps

1. Run test request (Step 7) to verify end-to-end workflow
2. Review [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for detailed schema information
3. Check [README.md](README.md) for API usage and architecture
4. Set up monitoring and logging for production
5. Configure backup strategy
6. Test disaster recovery procedures
