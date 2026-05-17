import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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
from app.models.employee_model import EmployeeTable

from app.llm.model_loader import load_llm
from app.agents.rag_agent import RAGAgent
from app.agents.subquestion_agent import SubQuestionAgent
from app.agents.graph_builder import build_and_run_graph

from app.utils.constants import EMPLOYEE_QUESTIONS, build_subquestions, TEMPLATE_PLACEHOLDERS
from app.utils.helpers import tmp_pdf_path, final_docx_path, utcnow

router = APIRouter(prefix="/api/v1", tags=["employee-review"])
logger = logging.getLogger(__name__)

# ── Module-level singletons (loaded once at import time, not per request) ──────
# This is critical — the LLM alone can be 700 MB–4 GB on disk.
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
    db: Session = Depends(get_db),       # ← session scoped to this request
):
    """
    Full pipeline:
      1.  OCR screenshot images
      2.  Load Zoom transcript
      3.  Merge OCR text + transcript → save as PDF
      4.  Chunk merged text
      5.  Embed chunks (batch)
      6.  Insert chunks + embeddings into pgvector
      7.  Build pgvector-backed RAG retriever
      8.  Fan-out: 7 questions × 3 subquestions run in parallel via LangGraph
      9.  Populate template_answer.docx with answers
      10. Return JSON response with all answers + docx path
    """
    emp_id = request.emp_id

    try:
        # ── 1. OCR ────────────────────────────────────────────────────────────
        logger.info("[1/9] OCR %d screenshot(s) for emp_id=%s", len(request.screenshot_paths), emp_id)
        ocr_text = _screenshot_svc.extract_all(request.screenshot_paths)

        # ── 2. Transcript ─────────────────────────────────────────────────────
        logger.info("[2/9] Load transcript: %s", request.transcript_path)
        transcript_text = _transcript_svc.load(request.transcript_path)

        # ── 3. Merge + PDF ────────────────────────────────────────────────────
        logger.info("[3/9] Merge text and save PDF")
        merged_text = (
            f"=== TRANSCRIPT ===\n\n{transcript_text}"
            f"\n\n=== SCREENSHOTS (OCR) ===\n\n{ocr_text}"
        )
        pdf_path = tmp_pdf_path(emp_id)
        _pdf_svc.save_pdf(merged_text, pdf_path)

        # ── 4. Chunk ──────────────────────────────────────────────────────────
        logger.info("[4/9] Chunk text")
        chunks = _chunk_svc.chunk(merged_text)
        logger.info("  → %d chunks produced", len(chunks))

        # ── 5 & 6. Embed + store in pgvector ─────────────────────────────────
        logger.info("[5/9] Embed and store chunks")
        repo = VectorRepository(db)
        embeddings = _embed_svc.embed_batch(chunks)
        now = utcnow()

        rows = [
            EmployeeTable(
                emp_id=emp_id,
                chunk=chunk,
                emb=embeddings[i],
                date_created=now,
                start_timestamp=str(i),      # use chunk index as placeholder timestamp
                screenshot_ids=request.screenshot_paths,
            )
            for i, chunk in enumerate(chunks)
        ]
        repo.insert_chunks_batch(rows)
        logger.info("  → %d rows inserted into pgvector", len(rows))

        # ── 7. Build RAG retriever ────────────────────────────────────────────
        logger.info("[6/9] Build RAG agent")
        llm       = _get_llm()
        retriever = repo.as_retriever(emp_id=emp_id)
        rag_agent = RAGAgent(llm=llm, retriever=retriever)

        # ── 8. Parallel 7×3 question graph ────────────────────────────────────
        logger.info("[7/9] Run LangGraph: 7 questions × 3 subquestions in parallel")
        raw_answers = await build_and_run_graph(
            rag_agent=rag_agent,
            subq_agent=_subq_agent,
            questions=EMPLOYEE_QUESTIONS,
            subquestions=_SUBQUESTIONS,
        )

        # ── 9. Populate .docx template ────────────────────────────────────────
        logger.info("[8/9] Populate .docx template")
        flat_answers = {
            TEMPLATE_PLACEHOLDERS[i]: raw_answers.get(q, {}).get("combined", "")
            for i, q in enumerate(EMPLOYEE_QUESTIONS)
        }
        docx_out = final_docx_path(emp_id, settings.OUTPUT_DIR)
        _template_svc.populate(settings.TEMPLATE_PATH, docx_out, flat_answers)

        # ── 10. Build and return response ─────────────────────────────────────
        logger.info("[9/9] Build JSON response")
        response_dto = build_response_dto(
            emp_id=emp_id,
            questions=EMPLOYEE_QUESTIONS,
            raw_answers=raw_answers,
            docx_path=docx_out,
        )
        return response_dto

    except Exception as exc:
        logger.exception("Pipeline failed for emp_id=%s", emp_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/download/{emp_id}")
def download_result(emp_id: str):
    """Download the generated final_answer.docx for a completed review."""
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
