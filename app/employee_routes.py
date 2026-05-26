import logging
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings

from app.schemas.request_dto import EmployeeRequestDTO
from app.schemas.response_dto import EmployeeResponseDTO
from app.schemas.serializer import build_response_dto

from app.services.screenshot_service import ScreenshotService
from app.services.transcript_service import TranscriptService
from app.services.pdf_service import PDFService
from app.services.chunk_service import ChunkService
from app.services.embedding_service import EmbeddingService
from app.services.template_service import TemplateService

from app.repositories.vector_repository import VectorRepository
from app.models.employee_model import Employee, EmployeeVersion, EmployeeVersionChunk

from app.llm.model_loader import load_llm
from app.agents.rag_agent import RAGAgent
from app.agents.subquestion_agent import SubQuestionAgent
from app.agents.graph_builder import build_and_run_graph

from app.utils.constants import EMPLOYEE_QUESTIONS, build_subquestions, TEMPLATE_PLACEHOLDERS
from app.utils.helpers import tmp_pdf_path, final_docx_path, utcnow

router = APIRouter(prefix="/api/v1", tags=["employee-review"])
logger = logging.getLogger(__name__)

# ── Module-level singletons (loaded once at import time, not per request) ──────
_llm            = None          # lazy: load on first request
_embed_svc      = EmbeddingService()
_screenshot_svc = ScreenshotService()
_transcript_svc = TranscriptService()
_pdf_svc        = PDFService()
_chunk_svc      = ChunkService()
_template_svc   = TemplateService()
_subq_agent     = SubQuestionAgent()

# Pre-build the static subquestion dict once
_SUBQUESTIONS = build_subquestions()


def _get_llm():
    global _llm
    if _llm is None:
        _llm = load_llm()
    return _llm


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/run-employee-review", response_model=EmployeeResponseDTO)
async def run_employee_review(
    request: EmployeeRequestDTO,
    db: Session = Depends(get_db),
):
    """
    Full production pipeline with proper data ingestion and retrieval:
      1.  Create/get employee record
      2.  Create version record
      3.  OCR screenshot images
      4.  Load Zoom transcript
      5.  Merge OCR text + transcript → save as PDF
      6.  Chunk merged text
      7.  Embed chunks and ingest into pgvector with proper relationships
      8.  Build pgvector-backed RAG retriever
      9.  Fan-out: 7 questions × 3 subquestions run in parallel via LangGraph
      10. Populate template_answer.docx with answers
      11. Return JSON response with version ID and results
    """
    emp_id = request.emp_id
    version = None

    try:
        repo = VectorRepository(db)

        # ── 1. Create/get employee ────────────────────────────────────────────
        logger.info("[1/11] Create/get employee record for emp_id=%s", emp_id)
        employee = repo.get_or_create_employee(
            emp_id=emp_id,
            emp_name=request.emp_name,
            department=request.department if hasattr(request, "department") else None,
        )
        logger.info("  → Employee: %s", employee)

        # ── 2. Create version ─────────────────────────────────────────────────
        logger.info("[2/11] Create version record for emp_id=%s", emp_id)
        version = repo.create_version(
            emp_id=emp_id,
            transcript_path=request.transcript_path,
            screenshot_paths=request.screenshot_paths,
        )
        logger.info("  → Version ID: %d, Version #%d, Status: %s", version.version_id, version.version, version.status)

        # ── 3. OCR ────────────────────────────────────────────────────────────
        logger.info("[3/11] OCR %d screenshot(s) for emp_id=%s", len(request.screenshot_paths), emp_id)
        ocr_text = _screenshot_svc.extract_all(request.screenshot_paths)

        # ── 4. Transcript ─────────────────────────────────────────────────────
        logger.info("[4/11] Load transcript: %s", request.transcript_path)
        transcript_text = _transcript_svc.load(request.transcript_path)

        # ── 5. Merge + PDF ────────────────────────────────────────────────────
        logger.info("[5/11] Merge text and save PDF")
        merged_text = (
            f"=== TRANSCRIPT ===\n\n{transcript_text}"
            f"\n\n=== SCREENSHOTS (OCR) ===\n\n{ocr_text}"
        )
        pdf_path = tmp_pdf_path(emp_id)
        _pdf_svc.save_pdf(merged_text, pdf_path)
        logger.info("  → PDF saved to: %s", pdf_path)

        # ── 6. Chunk ──────────────────────────────────────────────────────────
        logger.info("[6/11] Chunk text")
        chunks = _chunk_svc.chunk(merged_text)
        logger.info("  → %d chunks produced", len(chunks))

        # ── 7. Embed + ingest into pgvector with proper schema ────────────────
        logger.info("[7/11] Embed chunks and ingest into pgvector")
        chunk_rows, emb_rows = repo.insert_chunks_and_embeddings(
            version_id=version.version_id,
            emp_id=emp_id,
            chunks=chunks,
            metadata={},  # no per-chunk metadata for now
        )
        logger.info("  → %d chunks and %d embeddings ingested", len(chunk_rows), len(emb_rows))

        # Update version with PDF path
        repo.update_version_status(
            version_id=version.version_id,
            status="chunks_ingested",
            pdf_path=pdf_path,
        )

        # ── 8. Build RAG retriever ────────────────────────────────────────────
        logger.info("[8/11] Build RAG agent with pgvector retriever")
        llm = _get_llm()
        retriever = repo.as_retriever(
            emp_id=emp_id,
            version_id=version.version_id,
            top_k=5,
        )
        rag_agent = RAGAgent(llm=llm, retriever=retriever)
        logger.info("  → RAG agent ready with %d chunks", len(chunk_rows))

        # ── 9. Parallel 7×3 question graph ────────────────────────────────────
        logger.info("[9/11] Run LangGraph: 7 questions × 3 subquestions in parallel")
        raw_answers = await build_and_run_graph(
            rag_agent=rag_agent,
            subq_agent=_subq_agent,
            questions=EMPLOYEE_QUESTIONS,
            subquestions=_SUBQUESTIONS,
        )
        logger.info("  → Generated answers for %d questions", len(raw_answers))

        # ── 10. Populate .docx template ───────────────────────────────────────
        logger.info("[10/11] Populate .docx template")
        flat_answers = {
            TEMPLATE_PLACEHOLDERS[i]: raw_answers.get(q, {}).get("combined", "")
            for i, q in enumerate(EMPLOYEE_QUESTIONS)
        }
        docx_out = final_docx_path(emp_id, settings.OUTPUT_DIR)
        _template_svc.populate(settings.TEMPLATE_PATH, docx_out, flat_answers)
        logger.info("  → Template populated: %s", docx_out)

        # ── 11. Mark version as completed ─────────────────────────────────────
        repo.update_version_status(
            version_id=version.version_id,
            status="completed",
        )

        # ── 12. Build and return response ─────────────────────────────────────
        logger.info("[11/11] Build JSON response")
        response_dto = build_response_dto(
            emp_id=emp_id,
            questions=EMPLOYEE_QUESTIONS,
            raw_answers=raw_answers,
            docx_path=docx_out,
            version_id=version.version_id,
            version_number=version.version,
        )
        logger.info("✓ Pipeline completed successfully for emp_id=%s, version_id=%d", emp_id, version.version_id)
        return response_dto

    except Exception as exc:
        logger.exception("Pipeline failed for emp_id=%s", emp_id)
        
        # Mark version as failed with error message
        if version:
            repo = VectorRepository(db)
            repo.update_version_status(
                version_id=version.version_id,
                status="failed",
                error_message=str(exc),
            )
        
        raise HTTPException(status_code=500, detail=str(exc))


# ── Retrieval & Data Access Routes ────────────────────────────────────────────

@router.get("/employee/{emp_id}/versions")
def get_employee_versions(
    emp_id: str,
    db: Session = Depends(get_db),
):
    """Get all versions for an employee."""
    repo = VectorRepository(db)
    employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee {emp_id} not found")
    
    versions = db.query(EmployeeVersion).filter(
        EmployeeVersion.emp_id == emp_id
    ).order_by(EmployeeVersion.version.desc()).all()
    
    return {
        "emp_id": emp_id,
        "emp_name": employee.emp_name,
        "department": employee.department,
        "total_versions": len(versions),
        "versions": [
            {
                "version_id": v.version_id,
                "version": v.version,
                "status": v.status,
                "date_created": v.date_created.isoformat() if v.date_created else None,
                "chunk_count": len(v.chunks),
                "error_message": v.error_message,
            }
            for v in versions
        ],
    }


@router.get("/employee/{emp_id}/version/{version_id}/chunks")
def get_version_chunks(
    emp_id: str,
    version_id: int,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get chunks for a specific version."""
    repo = VectorRepository(db)
    
    # Verify version exists and belongs to employee
    version = db.query(EmployeeVersion).filter(
        EmployeeVersion.version_id == version_id,
        EmployeeVersion.emp_id == emp_id,
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found for emp_id {emp_id}")
    
    chunks = (
        db.query(EmployeeVersionChunk)
        .filter(
            EmployeeVersionChunk.version_id == version_id,
            EmployeeVersionChunk.emp_id == emp_id,
        )
        .order_by(EmployeeVersionChunk.chunk_index)
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    total_chunks = repo.count_chunks_in_version(version_id, emp_id)
    
    return {
        "emp_id": emp_id,
        "version_id": version_id,
        "total_chunks": total_chunks,
        "limit": limit,
        "offset": offset,
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "chunk_index": c.chunk_index,
                "text": c.chunk_text[:100] + "..." if len(c.chunk_text) > 100 else c.chunk_text,
                "full_text": c.chunk_text,
                "speaker": c.speaker,
                "start_timestamp": c.start_timestamp,
                "end_timestamp": c.end_timestamp,
            }
            for c in chunks
        ],
    }


@router.post("/employee/{emp_id}/version/{version_id}/search")
def search_version(
    emp_id: str,
    version_id: int,
    query: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Search for similar chunks in a specific version using pgvector similarity.
    """
    repo = VectorRepository(db)
    
    # Verify version exists and belongs to employee
    version = db.query(EmployeeVersion).filter(
        EmployeeVersion.version_id == version_id,
        EmployeeVersion.emp_id == emp_id,
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found for emp_id {emp_id}")
    
    # Search using pgvector
    results = repo.similarity_search(
        query=query,
        emp_id=emp_id,
        version_id=version_id,
        top_k=top_k,
    )
    
    return {
        "emp_id": emp_id,
        "version_id": version_id,
        "query": query,
        "results": [
            {
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.chunk_text[:100] + "..." if len(chunk.chunk_text) > 100 else chunk.chunk_text,
                "full_text": chunk.chunk_text,
                "similarity_distance": float(distance),  # lower = more similar
                "speaker": chunk.speaker,
                "start_timestamp": chunk.start_timestamp,
            }
            for chunk, emb, distance in results
        ],
    }


@router.get("/download/{emp_id}")
def download_result(emp_id: str):
    """Download the generated final_answer.docx for a completed review (latest version)."""
    path = final_docx_path(emp_id, settings.OUTPUT_DIR)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"No result found for emp_id={emp_id}. Run the pipeline first.",
        )
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{emp_id}_final_answer.docx",
    )


@router.get("/download/{emp_id}/version/{version_id}")
def download_version_result(emp_id: str, version_id: int, db: Session = Depends(get_db)):
    """Download the generated docx for a specific version."""
    version = db.query(EmployeeVersion).filter(
        EmployeeVersion.version_id == version_id,
        EmployeeVersion.emp_id == emp_id,
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found for emp_id {emp_id}")
    
    path = final_docx_path(emp_id, settings.OUTPUT_DIR)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"Result file not found for version {version_id}",
        )
    
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{emp_id}_v{version.version}_answer.docx",
    )
