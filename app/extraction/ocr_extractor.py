from contextlib import contextmanager
import logging
import os
from typing import Dict, Any, List

import pymupdf

logger = logging.getLogger(__name__)


@contextmanager
def suppress_c_stderr():
    """
    Suppresses native C/C++ engine stderr prints (such as Leptonica/Tesseract
    'Image too small to scale!!' or 'Line cannot be recognized!!').
    """
    try:
        null_fd = os.open(os.devnull, os.O_WRONLY)
        old_stderr_fd = os.dup(2)
        try:
            os.dup2(null_fd, 2)
            yield
        finally:
            os.dup2(old_stderr_fd, 2)
            os.close(old_stderr_fd)
            os.close(null_fd)
    except Exception:
        yield


def get_tessdata_path() -> str:
    """Returns local tessdata directory containing eng.traineddata."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "tessdata")


def extract_pdf_ocr(pdf_path: str) -> Dict[str, Any]:
    """
    Performs OCR on scanned PDF pages using PyMuPDF and embedded Tesseract.
    Returns extracted full text and page-by-page word/element bounding boxes.
    """
    try:
        if not pdf_path or not os.path.exists(pdf_path):
            raise ValueError(f"Invalid PDF path provided: {pdf_path}")

        tessdata_dir = get_tessdata_path()
        all_text_pages: List[str] = []
        all_elements: List[Dict[str, Any]] = []

        doc = pymupdf.open(pdf_path)
        try:
            with suppress_c_stderr():
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    try:
                        textpage = page.get_textpage_ocr(
                            tessdata=tessdata_dir,
                            language="eng",
                            dpi=150
                        )
                        page_text = page.get_text(textpage=textpage)
                        all_text_pages.append(page_text)

                        words = page.get_text("words", textpage=textpage)
                        for w in words:
                            # Format: (x0, y0, x1, y1, word, block_no, line_no, word_no)
                            all_elements.append({
                                "page": page_num,
                                "text": w[4],
                                "bbox": [w[0], w[1], w[2], w[3]]
                            })
                    except Exception as page_err:
                        logger.warning(f"OCR failed for page {page_num} of {pdf_path}: {page_err}")
                        continue
        finally:
            doc.close()

        full_text = "\n".join(all_text_pages)
        return {
            "text": full_text,
            "elements": all_elements
        }

    except Exception as err:
        logger.error(f"Error during OCR extraction on {pdf_path}: {err}")
        return {
            "text": "",
            "elements": []
        }


def convert_scanned_to_searchable_pdf(pdf_path: str, output_path: str) -> str:
    """
    Renders scanned PDF pages and layers OCR text to produce a searchable PDF.
    Enables downstream tools like pdfplumber to parse table structures seamlessly.
    """
    try:
        tessdata_dir = get_tessdata_path()
        src_doc = pymupdf.open(pdf_path)
        searchable_doc = pymupdf.open()

        try:
            with suppress_c_stderr():
                for page in src_doc:
                    pix = page.get_pixmap(dpi=150)
                    pdf_bytes = pix.pdfocr_tobytes(language="eng", tessdata=tessdata_dir)
                    page_doc = pymupdf.open("pdf", pdf_bytes)
                    searchable_doc.insert_pdf(page_doc)
                    page_doc.close()

            searchable_doc.save(output_path)
            logger.info(f"Generated searchable OCR PDF at {output_path}")
            return output_path

        finally:
            src_doc.close()
            searchable_doc.close()

    except Exception as err:
        logger.error(f"Failed to create searchable PDF from {pdf_path}: {err}")
        return pdf_path
