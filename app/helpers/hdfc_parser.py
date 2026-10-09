import logging
import re
from typing import List, Dict, Any, Optional

import pdfplumber

from app.helpers.base_parser import BaseBankParser
from app.helpers.generic_parser import GenericBankParser

logger = logging.getLogger(__name__)


class HDFCBankParser(BaseBankParser):
    """
    Parser specialized for HDFC Bank statements.
    Extracts structured transactions using normalized word coordinate binning.
    Supports both digital PDFs and searchable OCR PDFs.
    """

    def detect(self, text: str) -> bool:
        """Detects if the document text corresponds to an HDFC Bank statement."""
        try:
            if not text:
                return False
            upper_text = text.upper()
            return "HDFC BANK" in upper_text or "HDFC000" in upper_text or "HDFCBANK" in upper_text
        except Exception as err:
            logger.error(f"Error in HDFCBankParser.detect: {err}")
            return False

    def extract_account_info(self, text: str) -> Dict[str, Any]:
        """Extracts account holder name, account number, and IFSC from HDFC statement text."""
        try:
            info = {
                "account_name": None,
                "account_number": None,
                "ifsc": None
            }
            if not text:
                return info

            account_match = re.search(r'Account\s*(?:No|Number)?\s*[:\s]*([0-9]+)', text, re.I)
            if account_match:
                info["account_number"] = account_match.group(1).strip()

            ifsc_match = re.search(r'(?:RTGS/NEFT\s*)?IFSC\s*[:\s]*([A-Z0-9]+)', text, re.I)
            if ifsc_match:
                info["ifsc"] = ifsc_match.group(1).strip()
            else:
                generic_ifsc = re.search(r'\b(HDFC\d{7})\b', text, re.I)
                if generic_ifsc:
                    info["ifsc"] = generic_ifsc.group(1).strip()

            name_match = re.search(r'(?:MS|MR|MRS|M/S)\s+([A-Z\s]+?)(?:\r?\n|Account|$)', text, re.I)
            if name_match:
                info["account_name"] = name_match.group(1).strip()

            return info

        except Exception as err:
            logger.error(f"Error in HDFCBankParser.extract_account_info: {err}")
            return {
                "account_name": None,
                "account_number": None,
                "ifsc": None
            }

    def extract_transactions(self, text: str, pdf_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extracts tabular transactions from HDFC bank statement PDF.
        Falls back to generic text-based extraction if pdf_path is absent or yields 0 transactions.
        """
        try:
            transactions = []
            if pdf_path:
                transactions = self._extract_transactions_from_pdf(pdf_path)

            if not transactions and text:
                logger.info("HDFC tabular extraction yielded 0 transactions; attempting generic text parsing.")
                transactions = GenericBankParser().extract_transactions(text, pdf_path)

            return transactions

        except Exception as err:
            logger.error(f"Error in HDFCBankParser.extract_transactions: {err}")
            return []

    def _extract_transactions_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Internal method to parse HDFC statement transaction table using normalized coordinate binning."""
        try:
            transactions = []
            current_transaction = None
            date_pattern = re.compile(r'^\d{2}[/-]\d{2}[/-]\d{2,4}$')

            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    words = page.extract_words()
                    if not words:
                        continue

                    # Compute scale factor to normalize across differing resolutions/DPIs (standard page is 595 x 842 pt)
                    scale_x = 595.0 / page.width if page.width > 0 else 1.0
                    scale_y = 842.0 / page.height if page.height > 0 else 1.0

                    lines: Dict[int, list] = {}
                    for word in words:
                        # Normalize vertical position
                        norm_top = word["top"] * scale_y
                        y = round(norm_top / 2) * 2
                        if y not in lines:
                            lines[y] = []
                        lines[y].append(word)

                    for y in sorted(lines.keys()):
                        line_words = sorted(lines[y], key=lambda w: w["x0"] * scale_x)

                        col_data = {
                            "date": [],
                            "narration": [],
                            "chq": [],
                            "value_dt": [],
                            "withdrawal": [],
                            "deposit": [],
                            "balance": []
                        }

                        for w in line_words:
                            norm_x0 = w["x0"] * scale_x
                            if norm_x0 < 60:
                                col_data["date"].append(w["text"])
                            elif 60 <= norm_x0 < 280:
                                col_data["narration"].append(w["text"])
                            elif 280 <= norm_x0 < 360:
                                col_data["chq"].append(w["text"])
                            elif 360 <= norm_x0 < 400:
                                col_data["value_dt"].append(w["text"])
                            elif 400 <= norm_x0 < 480:
                                col_data["withdrawal"].append(w["text"])
                            elif 480 <= norm_x0 < 550:
                                col_data["deposit"].append(w["text"])
                            else:
                                col_data["balance"].append(w["text"])

                        date_text = " ".join(col_data["date"]).strip()
                        narration_text = " ".join(col_data["narration"]).strip()
                        full_line = " ".join([w["text"] for w in line_words]).strip()
                        full_line_upper = full_line.upper()

                        if "STATEMENTSUMMARY" in full_line_upper or "STATEMENT SUMMARY" in full_line_upper:
                            if current_transaction:
                                transactions.append(current_transaction)
                                current_transaction = None
                            break

                        if "Date" in date_text and "Narration" in narration_text:
                            continue

                        if any(marker in full_line_upper for marker in [
                            "HDFCBANKLIMITED", "CLOSINGBALANCEINCLUDES", "CONTENTSOFTHISSTATEMENT",
                            "STATEACCOUNTBRANCHGSTN", "HDFCBANKGSTIN", "REGISTEREDOFFICEADDRESS",
                            "NOMINATION:", "JOINTHOLDERS:", "STATEMENTOF ACCOUNT", "STATEMENT OF ACCOUNT",
                            "GENERATEDON:", "GENERATEDBY:", "THISISACOMPUTERGENERATED",
                            "NOTREQUIRESIGNATURE", "ACCOUNTBRANCH", "ODLIMIT", "CUSTID",
                            "ACCOUNTNO", "RTGS/NEFT", "MICR:", "BRANCHCODE", "ACCOUNTSTATUS",
                            "ACCOUNTTYPE", "PAGENO.", "FROM :", "OPENINGBALANCE", "*CLOSINGBALANCE"
                        ]):
                            continue

                        if "REGISTERED" in full_line_upper and ("TO :" in full_line_upper or "TO:" in full_line_upper):
                            continue

                        if date_pattern.match(date_text):
                            if current_transaction:
                                current_transaction["description"] = re.sub(
                                    r'\s+', ' ', current_transaction["description"]
                                ).strip()
                                transactions.append(current_transaction)

                            current_transaction = {
                                "date": date_text,
                                "description": narration_text,
                                "debit": " ".join(col_data["withdrawal"]).strip() or None,
                                "credit": " ".join(col_data["deposit"]).strip() or None,
                                "balance": " ".join(col_data["balance"]).strip() or None
                            }
                        elif current_transaction and narration_text:
                            current_transaction["description"] += f" {narration_text}"

            if current_transaction:
                current_transaction["description"] = re.sub(
                    r'\s+', ' ', current_transaction["description"]
                ).strip()
                transactions.append(current_transaction)

            return transactions

        except Exception as err:
            logger.error(f"Error during HDFC PDF table extraction from {pdf_path}: {err}")
            return []
