from abc import ABC, abstractmethod
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseBankParser(ABC):
    """
    Abstract base class for all bank statement parsers.
    Each parser must implement statement detection, account info extraction,
    and transaction extraction.
    """

    @abstractmethod
    def detect(self, text: str) -> bool:
        """Determines whether this parser handles the given statement text."""
        pass

    @abstractmethod
    def extract_account_info(self, text: str) -> Dict[str, Any]:
        """Extracts bank account details like account number, name, IFSC."""
        pass

    @abstractmethod
    def extract_transactions(self, text: str, pdf_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extracts list of transaction dictionaries from text or PDF file."""
        pass
