import logging
from typing import Optional, Any

import pandas as pd

logger = logging.getLogger(__name__)


def clean_amount(value: Any, allow_negative: bool = False) -> Optional[float]:
    """
    Cleans raw monetary values, strings, or numbers into standardized float amounts.
    Strips currency symbols, comma separators, DR/CR suffixes, and accounting parentheses.
    """
    try:
        if value is None or pd.isna(value):
            return None

        if isinstance(value, (int, float)):
            val_float = float(value)
            return val_float if allow_negative else abs(val_float)

        value_str = str(value).strip()
        if not value_str:
            return None

        # Check negative indicators (e.g. "(100)", "-100", "100 DR")
        is_negative = False
        upper_str = value_str.upper()
        if "DR" in upper_str or "-" in value_str or (value_str.startswith("(") and value_str.endswith(")")):
            is_negative = True

        # Strip currency symbols and formatting marks
        cleaned_str = (
            value_str.replace("₹", "")
                     .replace("$", "")
                     .replace("€", "")
                     .replace("£", "")
                     .replace(",", "")
                     .replace("CR", "")
                     .replace("cr", "")
                     .replace("DR", "")
                     .replace("dr", "")
                     .replace("-", "")
                     .replace("(", "")
                     .replace(")", "")
                     .strip()
        )

        if not cleaned_str:
            return None

        amount = float(cleaned_str)
        if allow_negative and is_negative:
            return -abs(amount)
        return abs(amount)

    except (ValueError, TypeError) as err:
        logger.debug(f"Unable to parse numeric amount from '{value}': {err}")
        return None
    except Exception as err:
        logger.error(f"Unexpected error cleaning amount '{value}': {err}")
        return None
