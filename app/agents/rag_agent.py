from langchain.chains import RetrievalQA
from langchain.schema import BaseRetriever
from app.llm.prompt_templates import RAG_PROMPT


class RAGAgent:
    """
    Wraps LangChain's RetrievalQA with a custom prompt.
    The retriever is scoped to one employee (emp_id filter inside PGVectorRetriever).

    run(question) is intentionally synchronous because llama.cpp is a
    blocking C extension.  We offload it to a thread pool in SubQuestionAgent.
    """

    def __init__(self, llm, retriever: BaseRetriever) -> None:
        self.chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",              # concatenate retrieved chunks into one prompt
            retriever=retriever,
            return_source_documents=False,
            chain_type_kwargs={"prompt": RAG_PROMPT},
        )

    def run(self, question: str) -> str:
        """Answer a single question using retrieved context. Blocking."""
        result = self.chain({"query": question})
        return result.get("result", "").strip()
