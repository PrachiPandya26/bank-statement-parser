import logging
import os
from typing import Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def export_to_excel(df: pd.DataFrame, account_info: Dict[str, Any], filepath: str) -> str:
    """
    Exports processed transaction DataFrame and account metadata into a multi-sheet Excel file.
    Sheet 1: Transactions (Date, Description, Debit, Credit, Balance, Category)
    Sheet 2: Account Information (Account metadata)
    Sheet 3: Category Summary (Aggregated totals per category)
    """
    try:
        parent_dir = os.path.dirname(os.path.abspath(filepath))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            # Sheet 1: Transactions
            df_export = df if not df.empty else pd.DataFrame(
                columns=["Date", "Description", "Debit", "Credit", "Balance", "Category"]
            )
            df_export.to_excel(writer, sheet_name="Transactions", index=False)

            # Sheet 2: Account Information
            metadata = account_info if account_info else {"Info": "No account metadata extracted"}
            metadata_df = pd.DataFrame([metadata])
            metadata_df.to_excel(writer, sheet_name="Account Information", index=False)

            # Sheet 3: Category Summary
            if not df.empty and "Category" in df.columns:
                cat_summary = (
                    df.groupby("Category")
                    .agg(
                        Transaction_Count=("Category", "count"),
                        Total_Debit=("Debit", "sum"),
                        Total_Credit=("Credit", "sum")
                    )
                    .reset_index()
                )
                cat_summary.to_excel(writer, sheet_name="Category Summary", index=False)
            else:
                pd.DataFrame(columns=["Category", "Transaction_Count", "Total_Debit", "Total_Credit"]).to_excel(
                    writer, sheet_name="Category Summary", index=False
                )

            # Adjust column widths for readability across all sheets
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    col_letter = column[0].column_letter
                    max_len = 0
                    for cell in column:
                        cell_str = str(cell.value or "")
                        if len(cell_str) > max_len:
                            max_len = len(cell_str)
                    worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 65)

        logger.info(f"Excel file successfully generated at {filepath}")
        return filepath

    except Exception as err:
        logger.error(f"Failed to export Excel file to {filepath}: {err}")
        raise IOError(f"Failed to export Excel file: {err}") from err


def export_to_csv(df: pd.DataFrame, filepath: str) -> str:
    """
    Exports processed transaction DataFrame to a standard CSV file.
    """
    try:
        parent_dir = os.path.dirname(os.path.abspath(filepath))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        df.to_csv(filepath, index=False)
        logger.info(f"CSV file successfully generated at {filepath}")
        return filepath

    except Exception as err:
        logger.error(f"Failed to export CSV file to {filepath}: {err}")
        raise IOError(f"Failed to export CSV file: {err}") from err
