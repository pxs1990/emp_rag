from typing import TypedDict, Dict, List, Any


class GraphState(TypedDict, total=False):
    """
    Shared state object threaded through the LangGraph.

    questions   : { question_text: [subquestion_1, subquestion_2, subquestion_3] }
    answers     : { question_text: { "sub_answers": {subq: ans}, "combined": str } }
    """
    questions: Dict[str, List[str]]
    answers:   Dict[str, Any]
