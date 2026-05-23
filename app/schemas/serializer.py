from typing import Dict, List, Any
from app.schemas.response_dto import EmployeeResponseDTO, QuestionAnswerDTO, SubAnswerDTO


def build_response_dto(
    emp_id: str,
    questions: List[str],
    raw_answers: Dict[str, Any],
    docx_path: str,
    version_id: int,
    version_number: int,
) -> EmployeeResponseDTO:
    """
    Assemble the final EmployeeResponseDTO from the LangGraph output.

    Parameters
    ----------
    emp_id         : Employee identifier
    questions      : List of 7 review questions
    raw_answers    : LangGraph output with shape:
                     {
                         "question_text": {
                             "sub_answers": {"subq1": "ans1", "subq2": "ans2", "subq3": "ans3"},
                             "combined":    "Synthesised answer text ...",
                         },
                         ...
                     }
    docx_path      : Path to generated docx file
    version_id     : Database version_id (for tracking)
    version_number : Version number for this employee

    Returns
    -------
    EmployeeResponseDTO with all fields populated
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

    return EmployeeResponseDTO(
        emp_id=emp_id,
        version_id=version_id,
        version=version_number,
        answers=answers,
        docx_path=docx_path,
    )
