from typing import Dict, List, Any
from app.schemas.response_dto import EmployeeResponseDTO, QuestionAnswerDTO, SubAnswerDTO
from app.models.employee_model import EmployeeTable


def serialize_employee_row(row: EmployeeTable) -> Dict:
    """Convert a single ORM row to a plain dict (for logging / debug)."""
    return {
        "emp_id":          row.emp_id,
        "chunk_preview":   (row.chunk or "")[:100],
        "date_created":    row.date_created.isoformat() if row.date_created else None,
        "speaker":         row.speaker,
        "start_timestamp": row.start_timestamp,
        "end_timestamp":   row.end_timestamp,
        "screenshot_ids":  row.screenshot_ids,
        "has_embedding":   row.emb is not None,
    }


def build_response_dto(
    emp_id: str,
    questions: List[str],
    raw_answers: Dict[str, Any],   # { question: {sub_answers:{subq:ans}, combined:str} }
    docx_path: str,
) -> EmployeeResponseDTO:
    """
    Assemble the final EmployeeResponseDTO from the LangGraph output.

    raw_answers shape:
        {
            "What are the employee's key strengths?": {
                "sub_answers": {"subq1": "ans1", "subq2": "ans2", "subq3": "ans3"},
                "combined":    "Synthesised answer text ...",
            },
            ...
        }
    """
    answers: Dict[str, QuestionAnswerDTO] = {}

    for i, question in enumerate(questions):
        data = raw_answers.get(question, {})
        sub_answers_raw: Dict[str, str] = data.get("sub_answers", {})
        combined: str = data.get("combined", "")

        sub_answer_dtos = [
            SubAnswerDTO(subquestion=subq, answer=ans)
            for subq, ans in sub_answers_raw.items()
        ]

        answers[f"Q{i + 1}"] = QuestionAnswerDTO(
            question=question,
            sub_answers=sub_answer_dtos,
            combined_answer=combined,
        )

    return EmployeeResponseDTO(emp_id=emp_id, answers=answers, docx_path=docx_path)
