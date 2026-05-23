from pydantic import BaseModel
from typing import Dict, Optional


class SubAnswerDTO(BaseModel):
    """One subquestion and its RAG-generated answer."""
    subquestion: str
    answer: str


class QuestionAnswerDTO(BaseModel):
    """One of the 7 employee review questions with 3 sub-answers."""
    question: str
    sub_answers: list[SubAnswerDTO]
    combined_answer: str  # synthesised from the 3 sub-answers


class EmployeeResponseDTO(BaseModel):
    """
    Full pipeline response body returned by POST /api/v1/run-employee-review.

    emp_id     : Employee identifier.
    version_id : Database version ID (for tracking and retrieval).
    version    : Version number for this employee.
    answers    : dict keyed "Q1"…"Q7", each a QuestionAnswerDTO.
    docx_path  : local path to the generated final_answer.docx.
    """
    emp_id: str
    version_id: int
    version: int
    answers: Dict[str, QuestionAnswerDTO]
    docx_path: str

    class Config:
        json_schema_extra = {
            "example": {
                "emp_id": "EMP-001",
                "version_id": 42,
                "version": 1,
                "answers": {
                    "Q1": {
                        "question": "What are the employee's key strengths?",
                        "sub_answers": [
                            {"subquestion": "... — detail 1", "answer": "Strong communication..."},
                            {"subquestion": "... — detail 2", "answer": "Consistent delivery..."},
                            {"subquestion": "... — detail 3", "answer": "Collaborative mindset..."},
                        ],
                        "combined_answer": "The employee demonstrates strong communication...",
                    }
                },
                "docx_path": "output/EMP-001_final_answer.docx",
            }
        }
