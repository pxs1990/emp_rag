from typing import List

from sentence_transformers import SentenceTransformer

from app.config.settings import settings


class EmbeddingService:
    """
    Converts text to 384-dimensional float vectors using all-MiniLM-L6-v2.

    The SentenceTransformer model is kept as a class-level singleton so
    multiple EmbeddingService instances never reload it from disk.
    """

    _model: SentenceTransformer | None = None

    def __init__(self) -> None:
        if EmbeddingService._model is None:
            EmbeddingService._model = SentenceTransformer(settings.EMBED_MODEL)

    def embed(self, text: str) -> List[float]:
        """Embed a single string → list[float] ready for pgvector."""
        return EmbeddingService._model.encode(
            text, convert_to_numpy=True
        ).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed many strings in one forward pass – faster than looping embed()."""
        vectors = EmbeddingService._model.encode(
            texts, convert_to_numpy=True, batch_size=32
        )
        return [v.tolist() for v in vectors]