from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from langchain.schema import BaseRetriever, Document
from langchain.callbacks.manager import CallbackManagerForRetrieverRun

from app.models.employee_model import (
    Employee, EmployeeVersion, EmployeeVersionChunk, EmployeeVersionEmb
)
from app.services.embedding_service import EmbeddingService


class VectorRepository:
    """
    Handles ingestion and retrieval for the emp_ai schema.
    Manages Employee → EmployeeVersion → Chunks → Embeddings hierarchy.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._embed_svc = EmbeddingService()

    # ── Employee Management ───────────────────────────────────────────────────

    def get_or_create_employee(self, emp_id: str, emp_name: str = None, department: str = None) -> Employee:
        """Get existing employee or create a new one."""
        emp = self.db.query(Employee).filter(Employee.emp_id == emp_id).first()
        if not emp:
            emp = Employee(
                emp_id=emp_id,
                emp_name=emp_name,
                department=department,
            )
            self.db.add(emp)
            self.db.commit()
            self.db.refresh(emp)
        return emp

    # ── Version Management ────────────────────────────────────────────────────

    def create_version(
        self,
        emp_id: str,
        transcript_path: str = None,
        screenshot_paths: List[str] = None,
    ) -> EmployeeVersion:
        """
        Create a new version record for an employee.
        Status starts as 'processing'.
        """
        # Ensure employee exists
        self.get_or_create_employee(emp_id)

        # Get next version number
        last_version = (
            self.db.query(EmployeeVersion)
            .filter(EmployeeVersion.emp_id == emp_id)
            .order_by(desc(EmployeeVersion.version))
            .first()
        )
        next_version_num = (last_version.version + 1) if last_version else 1

        version = EmployeeVersion(
            emp_id=emp_id,
            version=next_version_num,
            transcript_path=transcript_path,
            screenshot_paths=screenshot_paths or [],
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def update_version_status(
        self,
        version_id: int,
        status: str,
        pdf_path: str = None,
        error_message: str = None,
    ) -> EmployeeVersion:
        """Update version status and optional pdf_path or error_message."""
        version = self.db.query(EmployeeVersion).filter(
            EmployeeVersion.version_id == version_id
        ).first()
        if version:
            version.status = status
            if pdf_path:
                version.pdf_path = pdf_path
            if error_message:
                version.error_message = error_message
            self.db.commit()
            self.db.refresh(version)
        return version

    # ── Chunk & Embedding Ingestion ───────────────────────────────────────────

    def insert_chunks_and_embeddings(
        self,
        version_id: int,
        emp_id: str,
        chunks: List[str],
        metadata: dict = None,
    ) -> Tuple[List[EmployeeVersionChunk], List[EmployeeVersionEmb]]:
        """
        Bulk-insert chunks and their embeddings.
        
        Args:
            version_id: Version record ID
            emp_id: Employee ID
            chunks: List of chunk texts
            metadata: Optional dict with per-chunk metadata (timestamps, speakers, etc.)
        
        Returns:
            Tuple of (chunk_rows, embedding_rows)
        """
        if metadata is None:
            metadata = {}

        # Embed all chunks in batch
        embeddings_list = self._embed_svc.embed_batch(chunks)

        chunk_rows = []
        embedding_rows = []

        for i, chunk_text in enumerate(chunks):
            # Create chunk record
            chunk_row = EmployeeVersionChunk(
                version_id=version_id,
                emp_id=emp_id,
                chunk_text=chunk_text,
                chunk_index=i,
                start_timestamp=metadata.get(i, {}).get("start_timestamp"),
                end_timestamp=metadata.get(i, {}).get("end_timestamp"),
                speaker=metadata.get(i, {}).get("speaker"),
            )
            self.db.add(chunk_row)
            chunk_rows.append(chunk_row)

        # Flush to get chunk IDs
        self.db.flush()

        # Create embedding records
        for i, (chunk_row, emb_vector) in enumerate(zip(chunk_rows, embeddings_list)):
            emb_row = EmployeeVersionEmb(
                chunk_id=chunk_row.chunk_id,
                version_id=version_id,
                emp_id=emp_id,
                embedding=emb_vector,
            )
            self.db.add(emb_row)
            embedding_rows.append(emb_row)

        self.db.commit()
        return chunk_rows, embedding_rows

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def similarity_search(
        self,
        query: str,
        emp_id: str,
        version_id: int = None,
        top_k: int = 5,
    ) -> List[Tuple[EmployeeVersionChunk, EmployeeVersionEmb, float]]:
        """
        Search for chunks most similar to query using pgvector cosine distance.
        
        Returns list of (chunk, embedding, distance) tuples.
        If version_id is None, searches across all versions for the employee.
        """
        query_emb = self._embed_svc.embed(query)

        # Build query
        q = self.db.query(
            EmployeeVersionChunk,
            EmployeeVersionEmb,
            EmployeeVersionEmb.embedding.op("<=>")(query_emb).label("distance")
        ).filter(
            EmployeeVersionChunk.emp_id == emp_id,
            EmployeeVersionChunk.chunk_id == EmployeeVersionEmb.chunk_id,
        )

        if version_id:
            q = q.filter(EmployeeVersionChunk.version_id == version_id)

        results = q.order_by("distance").limit(top_k).all()
        return results

    def get_chunks_for_version(
        self,
        version_id: int,
        emp_id: str,
    ) -> List[EmployeeVersionChunk]:
        """Fetch all chunks for a specific version."""
        return (
            self.db.query(EmployeeVersionChunk)
            .filter(
                and_(
                    EmployeeVersionChunk.version_id == version_id,
                    EmployeeVersionChunk.emp_id == emp_id,
                )
            )
            .order_by(EmployeeVersionChunk.chunk_index)
            .all()
        )

    def get_embeddings_for_version(
        self,
        version_id: int,
        emp_id: str,
    ) -> List[EmployeeVersionEmb]:
        """Fetch all embeddings for a specific version."""
        return (
            self.db.query(EmployeeVersionEmb)
            .filter(
                and_(
                    EmployeeVersionEmb.version_id == version_id,
                    EmployeeVersionEmb.emp_id == emp_id,
                )
            )
            .all()
        )

    def count_chunks_in_version(self, version_id: int, emp_id: str) -> int:
        """Count chunks in a specific version."""
        return (
            self.db.query(EmployeeVersionChunk)
            .filter(
                and_(
                    EmployeeVersionChunk.version_id == version_id,
                    EmployeeVersionChunk.emp_id == emp_id,
                )
            )
            .count()
        )

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def delete_version(self, version_id: int) -> int:
        """Delete a version and all its chunks/embeddings. Returns deleted count."""
        # Cascade deletes via ORM relationships
        version = self.db.query(EmployeeVersion).filter(
            EmployeeVersion.version_id == version_id
        ).first()
        if version:
            self.db.delete(version)
            self.db.commit()
            return 1
        return 0

    def delete_employee(self, emp_id: str) -> int:
        """Delete an employee and all versions/chunks/embeddings. Returns deleted count."""
        emp = self.db.query(Employee).filter(Employee.emp_id == emp_id).first()
        if emp:
            self.db.delete(emp)
            self.db.commit()
            return 1
        return 0

    # ── LangChain adapter ─────────────────────────────────────────────────────

    def as_retriever(
        self,
        emp_id: str,
        version_id: int = None,
        top_k: int = 5,
    ) -> "PGVectorRetriever":
        """
        Return a LangChain-compatible retriever scoped to employee (and optionally version).
        """
        return PGVectorRetriever(
            repo=self,
            emp_id=emp_id,
            version_id=version_id,
            top_k=top_k,
        )


class PGVectorRetriever(BaseRetriever):
    """
    LangChain BaseRetriever backed by pgvector similarity search.
    Compatible with RetrievalQA.from_chain_type(retriever=...).
    """

    def __init__(
        self,
        repo: VectorRepository,
        emp_id: str,
        version_id: int = None,
        top_k: int = 5,
    ) -> None:
        object.__setattr__(self, "_repo", repo)
        object.__setattr__(self, "_emp_id", emp_id)
        object.__setattr__(self, "_version_id", version_id)
        object.__setattr__(self, "_top_k", top_k)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """Retrieve documents matching the query."""
        results = self._repo.similarity_search(
            query=query,
            emp_id=self._emp_id,
            version_id=self._version_id,
            top_k=self._top_k,
        )
        documents = [
            Document(
                page_content=chunk.chunk_text,
                metadata={
                    "chunk_id": chunk.chunk_id,
                    "version_id": chunk.version_id,
                    "emp_id": chunk.emp_id,
                    "chunk_index": chunk.chunk_index,
                    "speaker": chunk.speaker,
                    "start_timestamp": chunk.start_timestamp,
                    "distance": distance,
                },
            )
            for chunk, emb, distance in results
        ]
        return documents

    async def _aget_relevant_documents(self, query: str, **kwargs) -> List[Document]:
        """Async version of _get_relevant_documents."""
        return self._get_relevant_documents(query, **kwargs)
