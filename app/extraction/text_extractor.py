import logging

import pdfplumber
import pymupdf as fitz

logger = logging.getLogger(__name__)

def extract_pdf_text(pdf_path: str) -> str:
    """
    Extracts text from a text-based PDF using pdfplumber with PyMuPDF fallback.
    """
    pages = []
    # Primary extractor: pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                except Exception as page_err:
                    logger.warning(f"Failed extracting text from page {i} with pdfplumber: {page_err}")
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed on {pdf_path}: {e}. Trying pymupdf fallback...")

    # If pdfplumber extracted text, return it
    if pages:
        return "\n".join(pages)

    # Fallback extractor: pymupdf
    doc = None
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            try:
                text = page.get_text()
                if text:
                    pages.append(text)
            except Exception as page_err:
                logger.warning(f"Failed extracting text from page {i} with pymupdf: {page_err}")
        return "\n".join(pages)
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        raise RuntimeError(f"Failed to extract text from {pdf_path}: {e}") from e
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception as close_err:
                logger.warning(f"Error closing pymupdf document {pdf_path}: {close_err}")

