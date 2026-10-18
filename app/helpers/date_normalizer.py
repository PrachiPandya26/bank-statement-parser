import datetime
import logging
from typing import Optional, Any

from dateutil import parser

logger = logging.getLogger(__name__)


def normalize_date(value: Any) -> Optional[str]:
    """
    Normalizes a variety of input date formats into standard 'DD-MM-YY' string format.
    Handles dayfirst conventions standard in bank statements.
    """
    try:
        if not value:
            return None

        parsed_date: Optional[datetime.date] = None

        if isinstance(value, datetime.date):
            parsed_date = value
        elif isinstance(value, datetime.datetime):
            parsed_date = value.date()
        else:
            val_str = str(value).strip()
            if not val_str:
                return None
            parsed_date = parser.parse(val_str, dayfirst=True).date()

        if parsed_date:
            return parsed_date.strftime("%d-%m-%y")
        return None

    except (parser.ParserError, ValueError, TypeError) as err:
        logger.debug(f"Unable to parse date string '{value}': {err}")
        return None
    except Exception as err:
        logger.error(f"Unexpected error normalizing date '{value}': {err}")
        return None
