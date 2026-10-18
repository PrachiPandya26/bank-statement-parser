import logging
import os
import tempfile
from typing import Dict, Any, List, Tuple, Optional

import pandas as pd

from app.classification.rules import classify_transaction_rule_based
from app.classification.ml_classifier import classify_transaction_ml
from app.extraction.ocr_extractor import extract_pdf_ocr, convert_scanned_to_searchable_pdf
from app.extraction.pdf_detector import detect_pdf_type
from app.extraction.text_extractor import extract_pdf_text
from app.helpers.amount_normalizer import clean_amount
from app.helpers.base_parser import BaseBankParser
from app.helpers.date_normalizer import normalize_date
from app.helpers.export_helper import export_to_excel, export_to_csv
from app.helpers.generic_parser import GenericBankParser
from app.helpers.hdfc_parser import HDFCBankParser
from app.helpers.kotak_parser import KotakBankParser
from app.helpers.reconciliation_validator import validate_transaction

logger = logging.getLogger(__name__)


class StatementProcessingError(Exception):
    """Base exception for all statement processing errors."""
    pass


# Backward compatibility alias
ProcessingError = StatementProcessingError


class InvalidStatementFileError(StatementProcessingError):
    """Raised when the uploaded file is not a valid PDF or is empty."""
    pass


class StatementProcessorService:
    """
    Service layer handling end-to-end processing of bank statement documents:
    detection -> text/OCR extraction -> parsing -> normalization -> classification -> reconciliation -> export.
    Supports both native text-based PDFs and scanned image-based PDFs.
    """

    def __init__(self, parsers: Optional[List[BaseBankParser]] = None):
        """Initializes statement processor service with bank statement parsers."""
        try:
            self.parsers = parsers or [HDFCBankParser(), KotakBankParser(), GenericBankParser()]
        except Exception as err:
            logger.error(f"Failed to initialize parser list: {err}")
            self.parsers = [GenericBankParser()]

    def select_parser(self, text: str) -> BaseBankParser:
        """
        Selects the appropriate bank statement parser based on text indicators.
        Falls back to GenericBankParser.
        """
        try:
            for parser in self.parsers:
                if parser.detect(text):
                    logger.info(f"Selected parser: {parser.__class__.__name__}")
                    return parser
            return GenericBankParser()
        except Exception as err:
            logger.error(f"Error detecting parser: {err}. Defaulting to GenericBankParser.")
            return GenericBankParser()

    def detect_and_extract(self, file_path: str) -> Tuple[str, str]:
        """
        Detects if PDF is text-based or scanned, then extracts text accordingly.
        """
        try:
            pdf_type = detect_pdf_type(file_path)
            logger.info(f"Detected PDF type: {pdf_type} for {file_path}")

            if pdf_type == "text":
                raw_text = extract_pdf_text(file_path)
            else:
                ocr_result = extract_pdf_ocr(file_path)
                raw_text = ocr_result.get("text", "")

            if not raw_text or not raw_text.strip():
                logger.warning(f"No text extracted from PDF {file_path}. Trying fallback OCR extraction.")
                ocr_result = extract_pdf_ocr(file_path)
                raw_text = ocr_result.get("text", "")

            return pdf_type, raw_text
        except Exception as err:
            logger.error(f"Detection and extraction failed for {file_path}: {err}")
            raise StatementProcessingError(f"Failed to extract text from statement: {err}") from err

    def parse_statement(self, parser: BaseBankParser, raw_text: str, file_path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extracts account information and raw transactions using selected parser.
        """
        try:
            account_info = parser.extract_account_info(raw_text) or {}
            raw_transactions = parser.extract_transactions(raw_text, pdf_path=file_path) or []
            logger.info(f"Extracted {len(raw_transactions)} raw transactions.")
            return account_info, raw_transactions
        except Exception as err:
            logger.error(f"Failed to parse statement data: {err}")
            raise StatementProcessingError(f"Failed to extract transactions from statement: {err}") from err

    def normalize_and_classify_transactions(self, raw_transactions: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Cleans and normalizes dates and amounts, classifies categories (Rules -> ML),
        and verifies balance reconciliation.
        """
        try:
            processed_txns = []
            previous_balance = None

            for tx in raw_transactions:
                try:
                    date_val = normalize_date(tx.get("date", ""))
                    debit_val = clean_amount(tx.get("debit"))
                    credit_val = clean_amount(tx.get("credit"))
                    balance_val = clean_amount(tx.get("balance"), allow_negative=True)
                    desc_val = str(tx.get("description", "")).strip()

                    # Dual-tier Non-LLM Classification: Rule-based heuristics with ML fallback
                    category = classify_transaction_rule_based(desc_val)
                    if category == "Others":
                        ml_cat = classify_transaction_ml(desc_val)
                        if ml_cat and ml_cat != "Others":
                            category = ml_cat

                    # Validate arithmetic reconciliation
                    validation_status = validate_transaction(
                        previous_balance,
                        debit_val,
                        credit_val,
                        balance_val
                    )

                    if balance_val is not None:
                        previous_balance = balance_val

                    processed_txns.append({
                        "Date": date_val,
                        "Description": desc_val,
                        "Debit": debit_val,
                        "Credit": credit_val,
                        "Balance": balance_val,
                        "Category": category
                    })
                except Exception as item_err:
                    logger.warning(f"Error processing transaction row {tx}: {item_err}")
                    continue

            return pd.DataFrame(processed_txns)
        except Exception as err:
            logger.error(f"Error during transactions normalization/classification: {err}")
            raise StatementProcessingError(f"Failed to normalize transactions: {err}") from err

    def export_processed_data(
        self,
        df: pd.DataFrame,
        account_info: Dict[str, Any],
        original_filename: str,
        output_dir: str = "output"
    ) -> List[str]:
        """
        Exports the processed DataFrame to Excel and CSV in the specified output folder.
        Uses the exact base name of the input PDF (e.g., output/Test_Statement.xlsx).
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(original_filename))[0]
            excel_path = os.path.join(output_dir, f"{base_name}.xlsx")
            csv_path = os.path.join(output_dir, f"{base_name}.csv")

            export_to_excel(df, account_info, excel_path)
            export_to_csv(df, csv_path)

            return [excel_path, csv_path]
        except Exception as err:
            logger.error(f"Export failed for {original_filename}: {err}")
            raise StatementProcessingError(f"Failed to export files: {err}") from err

    def process_file_path(self, file_path: str, original_filename: str, output_dir: str = "output") -> Dict[str, Any]:
        """
        Core service execution pipeline using a file on disk.
        Handles both digital and scanned PDFs seamlessly.
        """
        try:
            if not os.path.exists(file_path):
                raise InvalidStatementFileError(f"Statement file not found: {file_path}")

            # 1. Detect and Extract Text
            pdf_type, raw_text = self.detect_and_extract(file_path)

            # If PDF is scanned, create a searchable OCR PDF layer for precise coordinate table extraction
            active_pdf_path = file_path
            tmp_ocr_pdf = None
            if pdf_type == "scanned":
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_ocr_pdf = tmp_file.name
                    convert_scanned_to_searchable_pdf(file_path, tmp_ocr_pdf)
                    active_pdf_path = tmp_ocr_pdf
                except Exception as ocr_conv_err:
                    logger.warning(f"Searchable OCR PDF generation failed: {ocr_conv_err}; using original file.")
                    active_pdf_path = file_path

            try:
                # 2. Select Parser and Extract Raw Data
                parser = self.select_parser(raw_text)
                account_info, raw_txns = self.parse_statement(parser, raw_text, active_pdf_path)

                # 3. Normalize, Classify, Reconcile
                df = self.normalize_and_classify_transactions(raw_txns)

                # 4. Export to Excel and CSV in the designated output folder
                exported_files = self.export_processed_data(
                    df,
                    account_info,
                    original_filename,
                    output_dir
                )

                return {
                    "status": "success",
                    "pdf_type": pdf_type,
                    "account_info": account_info,
                    "transactions_count": len(df),
                    "files_generated": exported_files
                }
            finally:
                if tmp_ocr_pdf and os.path.exists(tmp_ocr_pdf):
                    try:
                        os.unlink(tmp_ocr_pdf)
                    except Exception as cleanup_err:
                        logger.warning(f"Could not remove temporary OCR PDF {tmp_ocr_pdf}: {cleanup_err}")

        except StatementProcessingError:
            raise
        except Exception as err:
            logger.error(f"Unexpected error in StatementProcessorService.process_file_path: {err}")
            raise StatementProcessingError(f"Processing failed unexpectedly: {err}") from err

    def process_bytes(self, file_bytes: bytes, original_filename: str, output_dir: str = "output") -> Dict[str, Any]:
        """
        Processes statement from raw in-memory bytes.
        Creates a temporary file safely and ensures cleanup.
        """
        try:
            if not file_bytes:
                raise InvalidStatementFileError("Empty file content received.")

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name

                return self.process_file_path(tmp_path, original_filename, output_dir=output_dir)

            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception as cleanup_err:
                        logger.warning(f"Could not remove temporary file {tmp_path}: {cleanup_err}")
        except StatementProcessingError:
            raise
        except Exception as err:
            logger.error(f"Unexpected error in StatementProcessorService.process_bytes: {err}")
            raise StatementProcessingError(f"Failed to process statement bytes: {err}") from err

    async def process_uploaded_file(self, file: Any, output_dir: str = "output") -> Dict[str, Any]:
        """
        Validates uploaded file payload and processes it into structured reports.
        Encapsulates all file-reading and input-validation business logic.
        """
        try:
            if not file or not getattr(file, "filename", None):
                raise InvalidStatementFileError("A valid PDF file and filename must be provided.")

            filename = file.filename
            suffix = os.path.splitext(filename)[1].lower()
            if suffix != ".pdf":
                raise InvalidStatementFileError(f"Unsupported file format '{suffix}'. Only .pdf files are accepted.")

            try:
                content = await file.read()
            except Exception as read_err:
                logger.error(f"Failed to read uploaded file payload for '{filename}': {read_err}")
                raise InvalidStatementFileError("Unable to read uploaded file contents.") from read_err

            if not content:
                raise InvalidStatementFileError("Uploaded statement file is empty.")

            return self.process_bytes(content, filename, output_dir=output_dir)
        except StatementProcessingError:
            raise
        except Exception as err:
            logger.error(f"Unexpected error in process_uploaded_file: {err}")
            raise StatementProcessingError(f"Failed to process uploaded file: {err}") from err


statement_service = StatementProcessorService()


def process_statement_file(file_path: str, original_filename: str, output_dir: str = "output") -> Dict[str, Any]:
    """
    Backwards-compatible standalone function delegating to StatementProcessorService.
    """
    try:
        return statement_service.process_file_path(file_path, original_filename, output_dir=output_dir)
    except StatementProcessingError:
        raise
    except Exception as err:
        logger.error(f"Unhandled error in process_statement_file: {err}")
        raise StatementProcessingError(f"An unexpected error occurred during processing: {err}") from err


def process_statement_bytes(file_bytes: bytes, original_filename: str, output_dir: str = "output") -> Dict[str, Any]:
    """
    Service function to process statements directly from bytes.
    """
    try:
        return statement_service.process_bytes(file_bytes, original_filename, output_dir=output_dir)
    except StatementProcessingError:
        raise
    except Exception as err:
        logger.error(f"Unhandled error in process_statement_bytes: {err}")
        raise StatementProcessingError(f"An unexpected error occurred during processing: {err}") from err
