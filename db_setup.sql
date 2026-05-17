-- ============================================================
--  emp_genai  •  PostgreSQL + pgvector setup
--  Run this entire file once before starting the application.
-- ============================================================

-- 1. Create the database (run as superuser outside a transaction)
--    If you already have the DB, skip this line.
-- CREATE DATABASE emp_genai;

-- 2. Connect to the database, then run the rest:
-- \c emp_genai

-- 3. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 4. Create schema
CREATE SCHEMA IF NOT EXISTS emp_ai;

-- 5. Create employee table
CREATE TABLE IF NOT EXISTS emp_ai.employee (
    emp_id           TEXT         NOT NULL,         -- employee identifier (PK part 1)
    chunk            TEXT,                           -- raw text chunk from OCR / transcript
    emb              vector(384),                    -- 384-dim embedding (all-MiniLM-L6-v2)
    date_created     TIMESTAMP    DEFAULT NOW(),     -- row insert time
    start_timestamp  TEXT,                           -- transcript segment start time
    end_timestamp    TEXT,                           -- transcript segment end time
    speaker          TEXT,                           -- speaker label from transcript
    screenshot_ids   TEXT[],                         -- array of source screenshot file paths
    screenshot_url   TEXT,                           -- optional remote URL for screenshot

    -- Composite PK: one employee can have many chunks
    -- Use a surrogate serial if you prefer a simple single-column PK.
    CONSTRAINT employee_pkey PRIMARY KEY (emp_id, date_created, start_timestamp)
);

-- 6. IVFFlat index for fast cosine similarity search
--    Train only after you have at least 1 000 rows; for small datasets a
--    plain sequential scan (no index) is fine.
CREATE INDEX IF NOT EXISTS employee_emb_cosine_idx
    ON emp_ai.employee
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

-- 7. Regular index on emp_id for fast filtered queries
CREATE INDEX IF NOT EXISTS employee_emp_id_idx
    ON emp_ai.employee (emp_id);

-- Verify
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'emp_ai' AND table_name = 'employee'
ORDER BY ordinal_position;
