import logging
from typing import Optional

logger = logging.getLogger(__name__)


def validate_transaction(previous_balance: Optional[float], debit: Optional[float], credit: Optional[float], current_balance: Optional[float]) -> str:
    """
    Validates arithmetic reconciliation:
    Current Balance == Previous Balance + Credit - Debit
    Returns 'SUCCESS', 'FAILED_RECONCILIATION', or 'SKIPPED_NO_BALANCE'.
    """
    try:
        if previous_balance is None or current_balance is None:
            return "SKIPPED_NO_BALANCE"

        debit_val = abs(debit) if debit is not None else 0.0
        credit_val = abs(credit) if credit is not None else 0.0

        expected_balance = previous_balance + credit_val - debit_val

        # Allow slight floating point tolerance (0.02)
        if abs(expected_balance - current_balance) < 0.02:
            return "SUCCESS"
        else:
            logger.debug(
                f"Reconciliation mismatch: prev={previous_balance}, cr={credit_val}, "
                f"dr={debit_val}, expected={expected_balance}, current={current_balance}"
            )
            return "FAILED_RECONCILIATION"

    except Exception as err:
        logger.error(f"Error validating transaction arithmetic: {err}")
        return "VALIDATION_ERROR"
