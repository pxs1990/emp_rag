from sqlalchemy import (
    Column, String, Integer, DateTime, ARRAY, Text, ForeignKey, 
    UniqueConstraint, Index, func
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base


class Employee(Base):
    """
    ORM model for emp_ai.employee.
    Represents an employee with multiple review versions.
    """

    __tablename__ = "employee"
    __table_args__ = {"schema": "emp_ai"}

    # ── Primary key ───────────────────────────────────────────────────────────
    emp_id       = Column(String, primary_key=True, nullable=False, index=True)
    emp_name     = Column(String, nullable=True)
    department   = Column(String, nullable=True)
    date_created = Column(DateTime, server_default=func.now(), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    versions = relationship(
        "EmployeeVersion",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<Employee emp_id={self.emp_id!r} name={self.emp_name!r}>"


class EmployeeVersion(Base):
    """
    ORM model for emp_ai.employee_version.
    Represents a single review session for an employee.
    """

    __tablename__ = "employee_version"
    __table_args__ = (
        UniqueConstraint("emp_id", "version", name="uq_emp_version"),
        Index("idx_emp_version_date", "emp_id", "date_created"),
        {"schema": "emp_ai"}
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    version_id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Foreign key ───────────────────────────────────────────────────────────
    emp_id = Column(String, ForeignKey("emp_ai.employee.emp_id"), nullable=False, index=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    version           = Column(Integer, nullable=False, default=1)  # version number
    transcript_path   = Column(String, nullable=True)
    screenshot_paths  = Column(ARRAY(String), nullable=True)
    pdf_path          = Column(String, nullable=True)
    status            = Column(String, default="processing", nullable=False)  # processing, completed, failed
    error_message     = Column(Text, nullable=True)
    date_created      = Column(DateTime, server_default=func.now(), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    employee = relationship("Employee", back_populates="versions")
    chunks = relationship(
        "EmployeeVersionChunk",
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="joined"
    )
    embeddings = relationship(
        "EmployeeVersionEmb",
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self) -> str:
        return f"<EmployeeVersion emp_id={self.emp_id!r} version={self.version} status={self.status!r}>"


class EmployeeVersionChunk(Base):
    """
    ORM model for emp_ai.employee_version_chunk.
    Represents a text chunk from a review session.
    """

    __tablename__ = "employee_version_chunk"
    __table_args__ = (
        Index("idx_version_chunk_index", "version_id", "chunk_index"),
        Index("idx_emp_version_chunk", "emp_id", "version_id"),
        {"schema": "emp_ai"}
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    chunk_id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    version_id = Column(Integer, ForeignKey("emp_ai.employee_version.version_id"), nullable=False, index=True)
    emp_id = Column(String, ForeignKey("emp_ai.employee.emp_id"), nullable=False, index=True)

    # ── Chunk data ────────────────────────────────────────────────────────────
    chunk_text       = Column(Text, nullable=False)
    chunk_index      = Column(Integer, nullable=False)  # order within version
    start_timestamp  = Column(String, nullable=True)    # transcript timestamp
    end_timestamp    = Column(String, nullable=True)
    speaker          = Column(String, nullable=True)    # speaker label
    date_created     = Column(DateTime, server_default=func.now(), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    version = relationship("EmployeeVersion", back_populates="chunks")
    embeddings = relationship(
        "EmployeeVersionEmb",
        back_populates="chunk",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    def __repr__(self) -> str:
        preview = (self.chunk_text or "")[:50]
        return f"<EmployeeVersionChunk chunk_id={self.chunk_id} preview={preview!r}>"


class EmployeeVersionEmb(Base):
    """
    ORM model for emp_ai.employee_version_emb.
    Stores embeddings for chunks using pgvector (384-dim vectors).
    """

    __tablename__ = "employee_version_emb"
    __table_args__ = (
        Index("idx_emp_version_emb", "emp_id", "version_id"),
        Index("idx_chunk_emb", "chunk_id", "version_id"),
        {"schema": "emp_ai"}
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    emb_id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    chunk_id = Column(Integer, ForeignKey("emp_ai.employee_version_chunk.chunk_id"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("emp_ai.employee_version.version_id"), nullable=False, index=True)
    emp_id = Column(String, ForeignKey("emp_ai.employee.emp_id"), nullable=False, index=True)

    # ── Embedding ────────────────────────────────────────────────────────────
    embedding = Column(Vector(384), nullable=False)  # 384-dim vector from all-MiniLM-L6-v2
    date_created = Column(DateTime, server_default=func.now(), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    chunk = relationship("EmployeeVersionChunk", back_populates="embeddings")
    version = relationship("EmployeeVersion", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<EmployeeVersionEmb emb_id={self.emb_id} chunk_id={self.chunk_id}>"
