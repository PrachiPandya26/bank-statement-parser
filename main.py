import logging

from fastapi import FastAPI, HTTPException, status
import uvicorn

from app.api.statements import router as statements_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bank Statement Processor API",
    description="Automated system for processing, extracting, and classifying PDF bank statements without LLMs.",
    version="1.0.0"
)

app.include_router(statements_router, prefix="/statements", tags=["statements"])


@app.get("/", status_code=status.HTTP_200_OK)
def read_root():
    """
    Health check and welcome endpoint.
    Returns service availability status.
    """
    try:
        return {
            "status": "healthy",
            "message": "Welcome to the Bank Statement Processor API"
        }
    except Exception as err:
        logger.error(f"Error in root health check endpoint: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service unavailable"
        ) from err


if __name__ == "__main__":
    logger.info("Starting Bank Statement Processor API with Uvicorn on http://0.0.0.0:8000...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
