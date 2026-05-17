from sqlalchemy import Column, String, DateTime, ARRAY, Text
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.models.base import Base


class EmployeeTable(Base):
    """
    ORM model for emp_ai.employee.

    One row = one text chunk from an employee review session.
    The `emb` column stores a 384-dim cosine-similarity vector
    produced by sentence-transformers/all-MiniLM-L6-v2.

    Composite PK: (emp_id, date_created, start_timestamp) — an employee
    can have many chunks across multiple sessions.
    """

    __tablename__ = "employee"
    __table_args__ = {"schema": "emp_ai"}

    # ── Primary key columns ───────────────────────────────────────────────────
    emp_id          = Column(String,    primary_key=True, nullable=False)
    date_created    = Column(DateTime,  primary_key=True, server_default=func.now())
    start_timestamp = Column(String,    primary_key=True, nullable=True)

    # ── Payload columns ───────────────────────────────────────────────────────
    chunk           = Column(Text)               # raw text chunk
    emb             = Column(Vector(384))        # 384-dim embedding vector
    end_timestamp   = Column(String)             # transcript segment end
    speaker         = Column(String)             # transcript speaker label
    screenshot_ids  = Column(ARRAY(String))      # source screenshot paths
    screenshot_url  = Column(Text)               # optional remote URL

    def __repr__(self) -> str:
        preview = (self.chunk or "")[:50]
        return f"<EmployeeTable emp_id={self.emp_id!r} chunk={preview!r}>"
