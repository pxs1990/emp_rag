import os
from fpdf import FPDF


class PDFService:
    """
    Saves the merged OCR + transcript text as a PDF file for archiving.
    Uses fpdf2 (actively maintained fork of fpdf).

    Install: pip install fpdf2
    """

    def save_pdf(self, text: str, path: str) -> str:
        """Write text to a PDF at the given path. Returns the path."""
        # Create output directory if needed
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)

        for line in text.splitlines():
            # Encode to latin-1 (FPDF's default); replace characters it can't handle
            safe = line.encode("latin-1", errors="replace").decode("latin-1")
            pdf.multi_cell(0, 5, safe)

        pdf.output(path)
        return path
