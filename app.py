"""
TNM Staging FastAPI Application

RESTful API for automated TNM staging of lung cancer from PET-CT reports.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from pdf_to_markdown import MarkdownConverter, pdf_to_markdown_text
from workflow import run_tnm_staging_workflow
from models import TNMStaging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TNM Staging API",
    description="Automated TNM staging for lung cancer from PET-CT radiology reports using AI",
    version="1.0.0",
    contact={
        "name": "TNM Staging System",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT"
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Mistral converter (reuse across requests)
api_key = os.environ.get('MISTRAL_API_KEY')
if not api_key:
    logger.error("MISTRAL_API_KEY not found in environment")
    raise ValueError("MISTRAL_API_KEY environment variable not set")

converter = MarkdownConverter(api_key=api_key)


# Response Models
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class StagingRequest(BaseModel):
    report_text: str = Field(..., description="Markdown text of the radiology report")
    report_id: Optional[str] = Field(None, description="Optional report identifier")
    patient_id: Optional[str] = Field(None, description="Optional patient identifier")


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str


# API Endpoints

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/stage/pdf", response_model=dict)
async def stage_from_pdf(
    file: UploadFile = File(..., description="PET-CT report PDF file"),
    report_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Process a PET-CT PDF report and return TNM staging.
    
    Args:
        file: PDF file upload
        report_id: Optional report identifier
        patient_id: Optional patient identifier
        
    Returns:
        Complete TNM staging results
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are accepted."
        )
    
    temp_pdf_path = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            content = await file.read()
            temp_pdf.write(content)
            temp_pdf_path = temp_pdf.name
        
        logger.info(f"Processing PDF: {file.filename}")
        
        # Step 1: Convert PDF to Markdown
        logger.info("Converting PDF to markdown...")
        markdown_text = pdf_to_markdown_text(temp_pdf_path, converter, with_images=False)
        
        # Step 2: Run TNM staging workflow
        logger.info("Running TNM staging analysis...")
        result = run_tnm_staging_workflow(
            report_text=markdown_text,
            report_id=report_id or file.filename,
            patient_id=patient_id
        )
        
        if not result.get("success"):
            logger.error(f"Staging failed: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Staging analysis failed: {result.get('error')}"
            )
        
        logger.info(f"Successfully staged: {result['staging']['tnm_stage']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        # Cleanup: Schedule temp file deletion
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            if background_tasks:
                background_tasks.add_task(os.unlink, temp_pdf_path)
            else:
                try:
                    os.unlink(temp_pdf_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")


@app.post("/api/v1/stage/text", response_model=dict)
async def stage_from_text(request: StagingRequest):
    """
    Process markdown text of a PET-CT report and return TNM staging.
    
    Args:
        request: Staging request with markdown text
        
    Returns:
        Complete TNM staging results
    """
    try:
        logger.info(f"Processing text staging for report: {request.report_id}")
        
        # Run TNM staging workflow
        result = run_tnm_staging_workflow(
            report_text=request.report_text,
            report_id=request.report_id,
            patient_id=request.patient_id
        )
        
        if not result.get("success"):
            logger.error(f"Staging failed: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Staging analysis failed: {result.get('error')}"
            )
        
        logger.info(f"Successfully staged: {result['staging']['tnm_stage']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in text staging: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run the FastAPI app
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8022,
        reload=True,
        log_level="info"
    )
