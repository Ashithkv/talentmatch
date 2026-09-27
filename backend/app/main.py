"""
TalentMatch backend entrypoint.

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import resume, match

settings = get_settings()

app = FastAPI(
    title="TalentMatch API",
    description="Resume-to-job matching with transparent, Python-calculated scoring.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)
app.include_router(match.router)


@app.get("/health")
async def health():
    return {"status": "ok", "llm_configured": settings.has_valid_api_key}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    # Last-resort safety net so the API never leaks a raw traceback to the
    # client; specific, expected errors are already handled in the routes.
    raise HTTPException(status_code=500, detail=f"Unexpected server error: {exc}")
