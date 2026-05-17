import asyncio
from typing import List
from app.agents.rag_agent import RAGAgent


class SubQuestionAgent:
    """
    Runs all subquestions for one main question concurrently.

    asyncio.to_thread() offloads each blocking RAGAgent.run() call
    to a thread-pool worker so they execute in parallel without blocking
    the event loop.  return_exceptions=True means one failing subquestion
    returns a fallback string instead of crashing the whole question.
    """

    async def answer(
        self,
        rag_agent: RAGAgent,
        subquestions: List[str],
    ) -> List[str]:
        """
        Run all subquestions in parallel.
        Returns a list of answer strings in the same order as subquestions.
        """
        tasks = [asyncio.to_thread(rag_agent.run, q) for q in subquestions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r if isinstance(r, str) else f"[Error: {r}]"
            for r in results
        ]
