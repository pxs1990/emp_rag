from langchain.prompts import PromptTemplate

# ── RAG answer prompt ─────────────────────────────────────────────────────────
# Used inside RetrievalQA: {context} = retrieved chunks, {question} = subquestion.
RAG_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an HR analyst reviewing an employee performance session.
Use ONLY the context below to answer the question.
If the context does not contain enough information, say "Insufficient evidence."

Context:
{context}

Question: {question}

Answer (concise, factual, max 3 sentences):""",
)

# ── Synthesis prompt ──────────────────────────────────────────────────────────
# Combines 3 sub-answers into one paragraph for the main question.
SYNTHESIS_PROMPT = PromptTemplate(
    input_variables=["question", "sub_answers"],
    template="""You are an HR analyst.
Synthesise the 3 sub-answers below into one coherent answer for the main question.
Be concise. Use bullet points if listing multiple findings.

Main question: {question}

Sub-answers:
{sub_answers}

Synthesised answer:""",
)
