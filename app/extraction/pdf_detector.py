import logging

import pymupdf as fitz

logger = logging.getLogger(__name__)

def detect_pdf_type(pdf_path: str) -> str:
    """
    Detects if a PDF is text-based or scanned (image-based).
    Uses a heuristic based on the amount of text extracted per page.
    """
    doc = None
    try:
        doc = fitz.open(pdf_path)
        doc_len = len(doc)
        if doc_len == 0:
            logger.warning(f"PDF {pdf_path} has 0 pages, defaulting to scanned.")
            return "scanned"

        pages_with_text = 0
        for page in doc:
            try:
                text = page.get_text()
                if text and len(text.strip()) > 50:
                    pages_with_text += 1
            except Exception as page_err:
                logger.warning(f"Failed to extract text from page during detection: {page_err}")
                continue

        # If at least 20% of pages have text, treat as text-based
        if (pages_with_text / doc_len) >= 0.2:
            return "text"
        return "scanned"

    except Exception as e:
        logger.error(f"Error detecting PDF type for {pdf_path}: {e}")
        raise RuntimeError(f"Failed to detect PDF type: {e}") from e
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception as close_err:
                logger.warning(f"Error closing PDF document {pdf_path}: {close_err}")

