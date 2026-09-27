"""
PDF text extraction.

Deliberately simple: we pull raw text page by page with pdfplumber. We are
not trying to preserve layout or handle scanned/image-only PDFs (that would
need OCR, which is out of scope for a portfolio project).
"""

import io
import pdfplumber

from app.services.errors import InvalidPDFError, EmptyResumeError


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract plain text from a PDF file's raw bytes.

    Raises:
        InvalidPDFError: if the bytes cannot be parsed as a PDF at all.
        EmptyResumeError: if the PDF parses but contains no extractable text
            (e.g. a scanned image with no text layer).
    """
    if not file_bytes:
        raise InvalidPDFError("Uploaded file is empty.")

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
    except Exception as exc:
        # pdfplumber/pdfminer raise a variety of exception types for
        # corrupted or non-PDF input; we normalize all of them here.
        raise InvalidPDFError(f"Could not read the uploaded file as a PDF: {exc}") from exc

    full_text = "\n".join(pages_text).strip()

    if not full_text:
        raise EmptyResumeError(
            "No text could be extracted from this PDF. It may be a scanned "
            "image without a text layer."
        )

    return full_text
