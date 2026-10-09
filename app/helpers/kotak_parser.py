import logging
import re
from typing import List, Dict, Any, Optional

import pdfplumber
import pymupdf

from app.extraction.ocr_extractor import get_tessdata_path
from app.helpers.base_parser import BaseBankParser

logger = logging.getLogger(__name__)


class KotakBankParser(BaseBankParser):
    """
    Parser specialized for Kotak Mahindra Bank statements.
    Supports both digital PDFs (via pdfplumber tables) and scanned PDFs (via OCR block analysis).
    """

    def detect(self, text: str) -> bool:
        """Detects if document text corresponds to Kotak Mahindra Bank statement."""
        try:
            if not text:
                return False
            upper_text = text.upper()
            return "KOTAK" in upper_text or "KKBK" in upper_text or "KOTAK MAHINDRA" in upper_text
        except Exception as err:
            logger.error(f"Error in KotakBankParser.detect: {err}")
            return False

    def extract_account_info(self, text: str) -> Dict[str, Any]:
        """Extracts account holder name, account number, and IFSC from Kotak statement text."""
        try:
            info = {
                "account_name": None,
                "account_number": None,
                "ifsc": None
            }
            if not text:
                return info

            # Account Number: 10 to 18 digits following Account No.
            account_match = re.search(r'Account\s*(?:No|Number|\.)\s*[:\.]?\s*(\d{8,18})', text, re.I)
            if account_match:
                info["account_number"] = account_match.group(1).strip()

            # IFSC: KKBK followed by 7 alphanumeric characters
            ifsc_match = re.search(r'\b(KKBK[A-Z0-9]{7})\b', text, re.I)
            if ifsc_match:
                info["ifsc"] = ifsc_match.group(1).strip()

            # Name extraction
            name_match = re.search(r'([A-Za-z\s\.]+)\nCRN', text, re.I)
            if name_match:
                info["account_name"] = name_match.group(1).strip()
            else:
                alt_name = re.search(r'Account\s*No\.?\s*\d+\s*\n\s*([A-Za-z\s]+?)(?:\n|Account|$)', text, re.I)
                if alt_name:
                    info["account_name"] = alt_name.group(1).strip()

            return info

        except Exception as err:
            logger.error(f"Error in KotakBankParser.extract_account_info: {err}")
            return {
                "account_name": None,
                "account_number": None,
                "ifsc": None
            }

    def extract_transactions(self, text: str, pdf_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extracts transactions from Kotak statement.
        Tries digital table extraction first; falls back to OCR block extraction if scanned.
        """
        try:
            transactions = []
            if pdf_path:
                # 1. Digital PDF table extraction via pdfplumber
                transactions = self._extract_from_digital_tables(pdf_path)

                # 2. Scanned PDF fallback via OCR block extraction
                if not transactions:
                    transactions = self._extract_from_ocr_blocks(pdf_path)

            return transactions

        except Exception as err:
            logger.error(f"Error in KotakBankParser.extract_transactions: {err}")
            return []

    def _extract_from_digital_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extracts transactions from digital Kotak statement tables using pdfplumber."""
        try:
            txns = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for t in tables:
                        for row in t:
                            if not row or len(row) < 7:
                                continue
                            seq = str(row[0] or '').strip()
                            date = str(row[1] or '').strip()
                            desc = str(row[2] or '').strip()
                            chq = str(row[3] or '').strip()
                            withdrawal = str(row[4] or '').strip()
                            deposit = str(row[5] or '').strip()
                            balance = str(row[6] or '').strip()

                            if seq.isdigit() and date:
                                full_desc = (desc + ' ' + chq).strip().replace('\n', ' ')
                                txns.append({
                                    "date": date,
                                    "description": full_desc,
                                    "debit": withdrawal or None,
                                    "credit": deposit or None,
                                    "balance": balance or None
                                })
            return txns

        except Exception as err:
            logger.debug(f"Kotak digital table extraction yielded no results: {err}")
            return []

    def _extract_from_ocr_blocks(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extracts transactions from scanned Kotak statement via OCR blocks."""
        try:
            txns = []
            tessdata_dir = get_tessdata_path()
            date_regex = re.compile(r'^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$')
            doc = pymupdf.open(pdf_path)

            try:
                for page in doc:
                    tp = page.get_textpage_ocr(tessdata=tessdata_dir, language="eng", dpi=150)
                    blocks = page.get_text("blocks", textpage=tp)
                    for b in blocks:
                        text = b[4].strip()
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        # Format in OCR block: [seq, date, desc_line_1, desc_line_2..., amt, balance, extra...]
                        if len(lines) >= 4 and lines[0].isdigit() and date_regex.match(lines[1]):
                            date = lines[1]
                            # Identify numeric tokens at end of block
                            # Kotak has: withdrawal or deposit, followed by balance
                            num_tokens = []
                            desc_tokens = []
                            for tok in lines[2:]:
                                clean_tok = tok.replace(',', '').replace('₹', '').strip()
                                try:
                                    float(clean_tok)
                                    num_tokens.append(tok)
                                except ValueError:
                                    desc_tokens.append(tok)

                            debit = None
                            credit = None
                            balance = None

                            if len(num_tokens) >= 2:
                                balance = num_tokens[-1]
                                amt = num_tokens[-2]
                                # Check if transaction was withdrawal or deposit based on balance delta or keywords
                                debit = amt
                            elif len(num_tokens) == 1:
                                balance = num_tokens[0]

                            txns.append({
                                "date": date,
                                "description": " ".join(desc_tokens).strip(),
                                "debit": debit,
                                "credit": credit,
                                "balance": balance
                            })
            finally:
                doc.close()

            return txns

        except Exception as err:
            logger.error(f"Kotak OCR block extraction failed: {err}")
            return []
