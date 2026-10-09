import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.services.statement_processor import statement_service, StatementProcessingError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/process", status_code=status.HTTP_200_OK)
async def process_statement(file: UploadFile = File(...)):
    """
    HTTP route to process a bank statement PDF file.
    Delegates processing directly to the service layer with simple and clean error handling.
    """
    try:
        return await statement_service.process_uploaded_file(file)
    except StatementProcessingError as err:
        logger.error(f"Statement processing error: {err}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
    except Exception as err:
        logger.error(f"Unexpected server error: {err}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while processing the statement.") from err
