"""POST /resume/upload"""

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import ResumeUploadResponse
from app.services.pdf_extractor import extract_text_from_pdf
from app.services.errors import InvalidPDFError, EmptyResumeError
from app.services import llm_service
from app.services.errors import MissingAPIKeyError, LLMFailureError, InvalidExtractedDataError

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)) -> ResumeUploadResponse:
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()

    try:
        resume_text = extract_text_from_pdf(file_bytes)
    except InvalidPDFError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmptyResumeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        resume_data = llm_service.extract_resume_data(resume_text)
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMFailureError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except InvalidExtractedDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ResumeUploadResponse(resume_text=resume_text, resume=resume_data)
