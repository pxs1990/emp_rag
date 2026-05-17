import os
import pytesseract
from PIL import Image


class ScreenshotService:
    """
    Extracts text from employee screenshot images using Tesseract OCR.

    Install system dependency:
        macOS  : brew install tesseract
        Ubuntu : apt install tesseract-ocr
    """

    def extract_text(self, image_path: str) -> str:
        """OCR a single image and return cleaned text."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Screenshot not found: {image_path}")

        img = Image.open(image_path)

        # Tesseract needs RGB or grayscale — convert RGBA, palette, etc.
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        text = pytesseract.image_to_string(img, lang="eng")
        return text.strip()

    def extract_all(self, image_paths: list[str]) -> str:
        """OCR all screenshots and join with double newlines."""
        parts = [self.extract_text(p) for p in image_paths]
        return "\n\n".join(p for p in parts if p)
