"""POST /match, POST /analyze-resume"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AnalyzeResumeRequest,
    AnalyzeResumeResponse,
    MatchRequest,
    MatchResponse,
)
from app.services import llm_service
from app.services.errors import (
    MissingAPIKeyError,
    LLMFailureError,
    InvalidExtractedDataError,
    MissingJobDescriptionError,
    EmptyResumeError,
)
from app.matching.scorer import calculate_match

router = APIRouter(tags=["match"])


def _validate_inputs(resume_text: str, job_description: str | None = None) -> None:
    if not resume_text or not resume_text.strip():
        raise EmptyResumeError("Resume text is empty.")
    if job_description is not None and not job_description.strip():
        raise MissingJobDescriptionError("Job description is empty.")


@router.post("/analyze-resume", response_model=AnalyzeResumeResponse)
async def analyze_resume(payload: AnalyzeResumeRequest) -> AnalyzeResumeResponse:
    try:
        _validate_inputs(payload.resume_text)
        resume_data = llm_service.extract_resume_data(payload.resume_text)
    except EmptyResumeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMFailureError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except InvalidExtractedDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AnalyzeResumeResponse(resume=resume_data)


@router.post("/match", response_model=MatchResponse)
async def match(payload: MatchRequest) -> MatchResponse:
    try:
        _validate_inputs(payload.resume_text, payload.job_description)

        resume_data = llm_service.extract_resume_data(payload.resume_text)
        job_data = llm_service.extract_job_requirements(payload.job_description)

        # The score itself is 100% Python - see matching/scorer.py.
        match_result = calculate_match(resume_data, job_data, payload.resume_text)

        # The LLM only explains a score it did not calculate.
        match_result.explanation = llm_service.generate_explanation(match_result, job_data)

    except (EmptyResumeError, MissingJobDescriptionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMFailureError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except InvalidExtractedDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return MatchResponse(resume=resume_data, job=job_data, match=match_result)
