import json
import os


class TranscriptService:
    """
    Loads a Zoom recording transcript from disk.

    Supported formats:
        .txt   — plain Zoom VTT-style transcript or any plain text
        .json  — list of utterance dicts:
                 [{"speaker": "Alice", "text": "...", "start": "00:01", "end": "00:05"}, ...]
    """

    def load(self, path: str) -> str:
        """Return the full transcript as a single string."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Transcript not found: {path}")

        ext = os.path.splitext(path)[-1].lower()

        if ext == ".json":
            return self._load_json(path)

        return self._load_txt(path)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_txt(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def _load_json(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            lines = []
            for entry in data:
                speaker = entry.get("speaker", "Unknown")
                text    = entry.get("text", "").strip()
                start   = entry.get("start", "")
                end     = entry.get("end", "")
                ts      = f"[{start} → {end}] " if start else ""
                lines.append(f"{ts}[{speaker}]: {text}")
            return "\n".join(lines)

        # Fallback: raw dict or string
        return str(data)
