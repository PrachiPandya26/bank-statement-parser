import logging
import re
from typing import List, Dict, Any, Optional

from app.helpers.base_parser import BaseBankParser

logger = logging.getLogger(__name__)


class GenericBankParser(BaseBankParser):
    """
    Fallback bank statement parser using regex patterns.
    """

    def detect(self, text: str) -> bool:
        """Fallback parser that matches any statement text."""
        try:
            return bool(text and text.strip())
        except Exception as err:
            logger.error(f"Error in GenericBankParser.detect: {err}")
            return True

    def extract_account_info(self, text: str) -> Dict[str, Any]:
        """Extracts account number, IFSC, and account holder name."""
        try:
            info = {
                "account_name": None,
                "account_number": None,
                "ifsc": None
            }
            if not text:
                return info

            account_match = re.search(r'Account\s*(?:No|Number|#)?[:\s]*([A-Z0-9X\-]+)', text, re.I)
            if account_match:
                info["account_number"] = account_match.group(1).strip()

            ifsc_match = re.search(r'\b([A-Z]{4}0[A-Z0-9]{6})\b', text, re.I)
            if ifsc_match:
                info["ifsc"] = ifsc_match.group(1).strip()

            name_match = re.search(r'(?:Account\s*Holder|Name|Customer\s*Name)[:\s]*([A-Z\s]+?)(?:\r?\n|$)', text, re.I)
            if name_match:
                info["account_name"] = name_match.group(1).strip()

            return info

        except Exception as err:
            logger.error(f"Error in GenericBankParser.extract_account_info: {err}")
            return {
                "account_name": None,
                "account_number": None,
                "ifsc": None
            }

    def extract_transactions(self, text: str, pdf_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Line-by-line regex extraction for generic statement format.
        Matches lines starting with a date and extracts description, debit/credit, and balance.
        """
        try:
            transactions = []
            if not text:
                return transactions

            lines = text.split('\n')
            date_pattern = re.compile(r'^\s*(\d{2}[-/]\d{2}[-/]\d{2,4})')

            for line in lines:
                try:
                    line_clean = line.strip()
                    if not line_clean:
                        continue

                    match = date_pattern.match(line_clean)
                    if match:
                        parts = line_clean.split()
                        if len(parts) >= 4:
                            date = parts[0]
                            balance = parts[-1]
                            line_upper = line_clean.upper()

                            is_cr = "CR" in line_upper
                            is_dr = "DR" in line_upper

                            tokens_between = parts[1:-1]
                            amount = None
                            desc_parts = []

                            for tok in tokens_between:
                                tok_clean = tok.replace(',', '').replace('₹', '')
                                try:
                                    float(tok_clean)
                                    amount = tok_clean
                                except ValueError:
                                    if tok.upper() not in ["CR", "DR"]:
                                        desc_parts.append(tok)

                            desc = " ".join(desc_parts)

                            debit = None
                            credit = None
                            if is_cr:
                                credit = amount
                            elif is_dr:
                                debit = amount
                            else:
                                if amount and amount.startswith("-"):
                                    debit = amount.lstrip("-")
                                else:
                                    debit = amount

                            transactions.append({
                                "date": date,
                                "description": desc,
                                "debit": debit,
                                "credit": credit,
                                "balance": balance
                            })
                except Exception as line_err:
                    logger.warning(f"Error parsing line '{line}': {line_err}")
                    continue

            return transactions

        except Exception as err:
            logger.error(f"Error in GenericBankParser.extract_transactions: {err}")
            return []

