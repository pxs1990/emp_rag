from typing import Dict, List

# ── The 7 employee review questions ──────────────────────────────────────────
EMPLOYEE_QUESTIONS: List[str] = [
    "What are the employee's key strengths demonstrated in this session?",
    "What areas of improvement or development gaps were identified?",
    "How effectively did the employee communicate and collaborate?",
    "What specific achievements or contributions did the employee make?",
    "How did the employee handle challenges or difficult situations?",
    "What is the overall performance rating and justification for this employee?",
    "What are the recommended next steps or action items for this employee?",
]

# ── 3 subquestions per main question ─────────────────────────────────────────
def build_subquestions(
    questions: List[str] = EMPLOYEE_QUESTIONS,
    n_sub: int = 3,
) -> Dict[str, List[str]]:
    """
    Build the static subquestion dict used by the LangGraph.
    Returns: { question_text: [subq_1, subq_2, subq_3] }
    """
    return {
        q: [f"{q} — aspect {i + 1}" for i in range(n_sub)]
        for q in questions
    }


# ── Docx template placeholders ────────────────────────────────────────────────
# These tokens must exist verbatim inside templates/template_answer.docx
TEMPLATE_PLACEHOLDERS: List[str] = [
    f"{{{{Q{i + 1}_ANSWER}}}}" for i in range(len(EMPLOYEE_QUESTIONS))
]
# → ["{{Q1_ANSWER}}", "{{Q2_ANSWER}}", ..., "{{Q7_ANSWER}}"]

# ── Misc ──────────────────────────────────────────────────────────────────────
EMBEDDING_DIM = 384
TOP_K_RETRIEVAL = 5
