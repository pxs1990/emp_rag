import logging
from langchain_community.llms import LlamaCpp
from app.config.settings import settings

logger = logging.getLogger(__name__)


def load_llm() -> LlamaCpp:
    """
    Load a local GGUF model for CPU inference via llama.cpp.

    Called once at startup in the route module.  Subsequent calls in the
    same process reuse the cached module-level singleton.

    Recommended free CPU models
    ---------------------------
    TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf  — fastest, ~700 MB, good structured output
    Phi-2.Q4_K_M.gguf                       — smarter,  ~1.6 GB
    Mistral-7B-Instruct-v0.2.Q4_K_M.gguf   — best quality, ~4 GB, needs ≥8 GB RAM

    Download with huggingface-cli:
        huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF \
            --include "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" --local-dir models/
    """
    logger.info("Loading LLM from %s (threads=%d)", settings.MODEL_PATH, settings.LLM_THREADS)

    return LlamaCpp(
        model_path=settings.MODEL_PATH,
        temperature=0.1,              # low = deterministic; better for factual QA
        max_tokens=512,               # per sub-answer; raise for longer responses
        n_ctx=4096,                   # context window size
        n_threads=settings.LLM_THREADS,
        verbose=False,                # suppress llama.cpp debug output
    )
