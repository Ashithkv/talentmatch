"""
Pydantic models shared across routes and services.

Keeping every structure explicit here makes both the LLM's structured
output and the API's request/response contracts easy to validate and
easy to explain in an interview.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, field_validator


# ---------------------------------------------------------------------------
# Resume side
# ---------------------------------------------------------------------------

class ResumeData(BaseModel):
    """Structured information extracted from a candidate's resume."""

    name: Optional[str] = Field(default=None, description="Candidate full name")
    email: Optional[str] = Field(default=None, description="Candidate email address")
    phone: Optional[str] = Field(default=None, description="Candidate phone number")
    skills: List[str] = Field(default_factory=list)
    experience_years: float = Field(default=0, ge=0, description="Total years of professional experience")
    education: List[str] = Field(default_factory=list)
    raw_text_length: int = Field(default=0, description="Length of extracted resume text, for debugging")

    @field_validator("skills", "education", mode="before")
    @classmethod
    def _dedupe_and_clean(cls, value):
        if not value:
            return []
        cleaned = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                continue
            item = item.strip()
            key = item.lower()
            if item and key not in seen:
                seen.add(key)
                cleaned.append(item)
        return cleaned


# ---------------------------------------------------------------------------
# Job description side
# ---------------------------------------------------------------------------

class JobRequirements(BaseModel):
    """Structured requirements extracted from a job description."""

    job_title: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    minimum_experience: float = Field(default=0, ge=0)
    location: Optional[str] = None

    @field_validator("required_skills", "preferred_skills", mode="before")
    @classmethod
    def _dedupe_and_clean(cls, value):
        if not value:
            return []
        cleaned = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                continue
            item = item.strip()
            key = item.lower()
            if item and key not in seen:
                seen.add(key)
                cleaned.append(item)
        return cleaned


# ---------------------------------------------------------------------------
# Matching output
# ---------------------------------------------------------------------------

class SkillBreakdown(BaseModel):
    matched_required: List[str] = Field(default_factory=list)
    missing_required: List[str] = Field(default_factory=list)
    matched_preferred: List[str] = Field(default_factory=list)
    missing_preferred: List[str] = Field(default_factory=list)
    skill_score: float = 0.0  # 0-100, this component only


class ExperienceBreakdown(BaseModel):
    candidate_years: float = 0.0
    required_years: float = 0.0
    meets_requirement: bool = False
    experience_score: float = 0.0  # 0-100, this component only


class TitleBreakdown(BaseModel):
    candidate_signal: Optional[str] = None
    job_title: Optional[str] = None
    title_score: float = 0.0  # 0-100, this component only


class LocationBreakdown(BaseModel):
    candidate_location: Optional[str] = None
    job_location: Optional[str] = None
    matches: bool = False
    location_score: float = 0.0  # 0-100, this component only


class MatchResult(BaseModel):
    overall_score: float = Field(..., ge=0, le=100)
    skills: SkillBreakdown
    experience: ExperienceBreakdown
    title: TitleBreakdown
    location: LocationBreakdown
    explanation: str = ""


# ---------------------------------------------------------------------------
# API request/response envelopes
# ---------------------------------------------------------------------------

class AnalyzeResumeRequest(BaseModel):
    resume_text: str = Field(..., min_length=1)


class AnalyzeResumeResponse(BaseModel):
    resume: ResumeData


class MatchRequest(BaseModel):
    resume_text: str = Field(..., min_length=1)
    job_description: str = Field(..., min_length=1)


class MatchResponse(BaseModel):
    resume: ResumeData
    job: JobRequirements
    match: MatchResult


class ResumeUploadResponse(BaseModel):
    resume_text: str
    resume: ResumeData
