from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter


class ChunkService:
    """
    Splits long merged text into overlapping chunks ready for embedding.

    chunk_size    = 1 000 chars  (~200–250 tokens for most models)
    chunk_overlap = 200 chars    (preserves context across boundaries)
    """

    def __init__(self) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            # Split on paragraph → sentence → word → character
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, text: str) -> List[str]:
        """Return a list of non-empty text chunks."""
        raw = self._splitter.split_text(text)
        return [c.strip() for c in raw if c.strip()]
