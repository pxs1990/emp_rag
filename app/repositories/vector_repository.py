from typing import List
from datetime import datetime

from sqlalchemy.orm import Session
from langchain.schema import BaseRetriever, Document
from langchain.callbacks.manager import CallbackManagerForRetrieverRun

from app.models.employee_model import EmployeeTable
from app.services.embedding_service import EmbeddingService


class VectorRepository:
    """
    Handles pgvector insert and cosine similarity search for the employee table.
    Also exposes as_retriever() to give LangChain's RetrievalQA a compatible object.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._embed_svc = EmbeddingService()

    # ── Write ─────────────────────────────────────────────────────────────────

    def insert_chunk(self, row: EmployeeTable) -> None:
        """Persist one chunk row and flush immediately."""
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)

    def insert_chunks_batch(self, rows: List[EmployeeTable]) -> None:
        """Bulk-insert many rows — faster than calling insert_chunk in a loop."""
        self.db.add_all(rows)
        self.db.commit()

    # ── Read ──────────────────────────────────────────────────────────────────

    def similarity_search(
        self,
        query: str,
        emp_id: str,
        top_k: int = 5,
    ) -> List[EmployeeTable]:
        """
        Return the top_k chunks most similar to `query` for a given employee.
        Uses pgvector's cosine distance operator (<=>) for ranking.
        """
        query_emb = self._embed_svc.embed(query)
        return (
            self.db.query(EmployeeTable)
            .filter(EmployeeTable.emp_id == emp_id)
            .order_by(EmployeeTable.emb.op("<=>")(query_emb))
            .limit(top_k)
            .all()
        )

    def count_chunks(self, emp_id: str) -> int:
        """How many chunks are stored for this employee."""
        return (
            self.db.query(EmployeeTable)
            .filter(EmployeeTable.emp_id == emp_id)
            .count()
        )

    def delete_by_emp_id(self, emp_id: str) -> int:
        """Remove all rows for an employee. Returns deleted row count."""
        n = (
            self.db.query(EmployeeTable)
            .filter(EmployeeTable.emp_id == emp_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return n

    # ── LangChain adapter ─────────────────────────────────────────────────────

    def as_retriever(self, emp_id: str, top_k: int = 5) -> "PGVectorRetriever":
        """Return a LangChain-compatible retriever scoped to one employee."""
        return PGVectorRetriever(repo=self, emp_id=emp_id, top_k=top_k)


class PGVectorRetriever(BaseRetriever):
    """
    LangChain BaseRetriever backed by our pgvector similarity_search.
    Passed directly into RetrievalQA.from_chain_type(retriever=...).
    """

    def __init__(self, repo: VectorRepository, emp_id: str, top_k: int = 5) -> None:
        # Use object.__setattr__ to bypass Pydantic field validation
        object.__setattr__(self, "_repo", repo)
        object.__setattr__(self, "_emp_id", emp_id)
        object.__setattr__(self, "_top_k", top_k)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        rows = self._repo.similarity_search(query, self._emp_id, self._top_k)
        return [
            Document(
                page_content=row.chunk,
                metadata={
                    "emp_id":          row.emp_id,
                    "speaker":         row.speaker,
                    "start_timestamp": row.start_timestamp,
                },
            )
            for row in rows
        ]
