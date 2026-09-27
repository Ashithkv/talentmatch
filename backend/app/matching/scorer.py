"""
Deterministic, transparent match scoring.

This is the heart of the "why doesn't the LLM just generate the score"
answer: every number here is produced by plain Python arithmetic that you
can log, unit test, and explain line by line. The LLM is only used
afterwards, to phrase the result in English (see services/llm_service.py).

Weighting (documented, not hidden):
    Skills match:            50%
    Experience match:        25%
    Job title/role relevance: 15%
    Location match:          10%
"""

import re
from typing import List, Optional

from app.models.schemas import (
    ResumeData,
    JobRequirements,
    MatchResult,
    SkillBreakdown,
    ExperienceBreakdown,
    TitleBreakdown,
    LocationBreakdown,
)

WEIGHT_SKILLS = 0.50
WEIGHT_EXPERIENCE = 0.25
WEIGHT_TITLE = 0.15
WEIGHT_LOCATION = 0.10

# Words too generic to count as a meaningful title-relevance signal
_STOPWORDS = {"the", "and", "for", "with", "our", "a", "an", "of", "to", "in", "on"}


def _normalize(text: str) -> str:
    return text.strip().lower()


def _score_skills(resume: ResumeData, job: JobRequirements) -> SkillBreakdown:
    candidate_skills = {_normalize(s) for s in resume.skills}

    def split_matches(required: List[str]):
        matched, missing = [], []
        for skill in required:
            if _normalize(skill) in candidate_skills:
                matched.append(skill)
            else:
                missing.append(skill)
        return matched, missing

    matched_required, missing_required = split_matches(job.required_skills)
    matched_preferred, missing_preferred = split_matches(job.preferred_skills)

    if job.required_skills:
        required_ratio = len(matched_required) / len(job.required_skills)
    else:
        # No required skills stated - don't penalize the candidate for that.
        required_ratio = 1.0

    if job.preferred_skills:
        preferred_ratio = len(matched_preferred) / len(job.preferred_skills)
    else:
        preferred_ratio = 1.0

    # Required skills carry most of the weight within this component;
    # preferred skills give a smaller bonus/penalty on top.
    skill_score = (required_ratio * 0.8 + preferred_ratio * 0.2) * 100

    return SkillBreakdown(
        matched_required=matched_required,
        missing_required=missing_required,
        matched_preferred=matched_preferred,
        missing_preferred=missing_preferred,
        skill_score=round(skill_score, 2),
    )


def _score_experience(resume: ResumeData, job: JobRequirements) -> ExperienceBreakdown:
    required_years = job.minimum_experience or 0
    candidate_years = resume.experience_years or 0

    if required_years <= 0:
        # Nothing required - candidate automatically satisfies it.
        score = 100.0
        meets = True
    elif candidate_years >= required_years:
        score = 100.0
        meets = True
    else:
        # Partial credit, proportional to how close they are.
        score = max(0.0, (candidate_years / required_years) * 100)
        meets = False

    return ExperienceBreakdown(
        candidate_years=candidate_years,
        required_years=required_years,
        meets_requirement=meets,
        experience_score=round(score, 2),
    )


def _score_title(resume_text: str, job: JobRequirements) -> TitleBreakdown:
    if not job.job_title:
        # No title stated in the JD - treat as neutral, don't penalize.
        return TitleBreakdown(candidate_signal=None, job_title=None, title_score=100.0)

    title_words = [
        w for w in re.findall(r"[a-zA-Z]+", job.job_title.lower())
        if w not in _STOPWORDS and len(w) > 2
    ]

    if not title_words:
        return TitleBreakdown(candidate_signal=None, job_title=job.job_title, title_score=100.0)

    resume_lower = resume_text.lower()
    found = [w for w in title_words if w in resume_lower]
    ratio = len(found) / len(title_words)
    score = ratio * 100

    signal = f"Found title keywords in resume: {', '.join(found)}" if found else None

    return TitleBreakdown(
        candidate_signal=signal,
        job_title=job.job_title,
        title_score=round(score, 2),
    )


def _score_location(resume_text: str, job: JobRequirements) -> LocationBreakdown:
    if not job.location:
        return LocationBreakdown(candidate_location=None, job_location=None, matches=True, location_score=100.0)

    job_location_lower = job.location.lower().strip()
    resume_lower = resume_text.lower()

    # Simple substring check: does the resume mention the job's stated
    # location (city/region/"remote")? Good enough for a portfolio project;
    # a production version would use geocoding/normalized location data.
    matches = job_location_lower in resume_lower

    candidate_location: Optional[str] = job.location if matches else None
    score = 100.0 if matches else 0.0

    return LocationBreakdown(
        candidate_location=candidate_location,
        job_location=job.location,
        matches=matches,
        location_score=score,
    )


def calculate_match(resume: ResumeData, job: JobRequirements, resume_text: str) -> MatchResult:
    """
    Compute the full, transparent match result. No LLM calls happen here -
    every field is calculated with plain arithmetic so the result is
    reproducible and explainable.
    """
    skills = _score_skills(resume, job)
    experience = _score_experience(resume, job)
    title = _score_title(resume_text, job)
    location = _score_location(resume_text, job)

    overall = (
        skills.skill_score * WEIGHT_SKILLS
        + experience.experience_score * WEIGHT_EXPERIENCE
        + title.title_score * WEIGHT_TITLE
        + location.location_score * WEIGHT_LOCATION
    )

    return MatchResult(
        overall_score=round(overall, 2),
        skills=skills,
        experience=experience,
        title=title,
        location=location,
        explanation="",  # filled in by the caller after the LLM explanation step
    )
