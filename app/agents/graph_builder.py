import asyncio
from typing import Dict, Any, List

from app.agents.state import GraphState
from app.agents.rag_agent import RAGAgent
from app.agents.subquestion_agent import SubQuestionAgent


# ── Node factory ──────────────────────────────────────────────────────────────

def make_question_node(
    rag_agent: RAGAgent,
    subq_agent: SubQuestionAgent,
    question: str,
    subquestions: List[str],
    node_key: str,
):
    """
    Returns an async coroutine function that acts as one LangGraph node.
    Each node answers one main question by running its 3 subquestions
    concurrently via SubQuestionAgent.
    """

    async def node_fn(state: GraphState) -> GraphState:
        # Run all 3 subquestions in parallel
        sub_answers_list = await subq_agent.answer(rag_agent, subquestions)

        # Build sub_answers dict: { subquestion_text: answer_text }
        sub_answers = {subquestions[i]: sub_answers_list[i] for i in range(len(subquestions))}

        # Simple synthesis: join sub-answers (replace with LLM synthesis if needed)
        combined = "\n\n".join(
            f"• {subquestions[i]}\n  {sub_answers_list[i]}"
            for i in range(len(subquestions))
        )

        updated_answers = dict(state.get("answers", {}))
        updated_answers[question] = {
            "sub_answers": sub_answers,
            "combined":    combined,
        }

        return {**state, "answers": updated_answers}

    node_fn.__name__ = node_key
    return node_fn


# ── Public entry point ────────────────────────────────────────────────────────

async def build_and_run_graph(
    rag_agent: RAGAgent,
    subq_agent: SubQuestionAgent,
    questions: List[str],
    subquestions: Dict[str, List[str]],
) -> Dict[str, Any]:
    """
    Fan-out: all 7 question nodes run concurrently with asyncio.gather.
    Each node itself runs its 3 subquestions concurrently via SubQuestionAgent.

    Total concurrent RAG calls = 7 questions × 3 subquestions = 21 threads.

    Returns
    -------
    dict keyed by question string:
        {
            "What are the employee's key strengths?": {
                "sub_answers": { subq: ans, ... },
                "combined":    "synthesised text ...",
            },
            ...
        }
    """
    initial_state: GraphState = {
        "questions": subquestions,
        "answers":   {},
    }

    # Create one coroutine per question
    tasks = [
        make_question_node(rag_agent, subq_agent, q, subquestions[q], f"q{i}")(initial_state)
        for i, q in enumerate(questions)
    ]

    # Run all questions in parallel; each returns a partial state
    partial_states = await asyncio.gather(*tasks)

    # Merge all partial answer dicts into one
    merged: Dict[str, Any] = {}
    for ps in partial_states:
        merged.update(ps.get("answers", {}))

    return merged
