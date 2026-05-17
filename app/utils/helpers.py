import os
from datetime import datetime


def tmp_pdf_path(emp_id: str, output_dir: str = "/tmp") -> str:
    """Return the path for a merged PDF file."""
    return os.path.join(output_dir, f"{emp_id}_merged.pdf")


def final_docx_path(emp_id: str, output_dir: str = "output") -> str:
    """Return the path for the final populated .docx."""
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, f"{emp_id}_final_answer.docx")


def utcnow() -> datetime:
    """UTC timestamp — single point for easy mocking in tests."""
    return datetime.utcnow()


def safe_filename(name: str) -> str:
    """Strip characters that break file paths."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
