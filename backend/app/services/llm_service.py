"""
All OpenAI calls live here, and only here.

The LLM has exactly three jobs in this app:
  1. Turn messy resume text into structured ResumeData.
  2. Turn a job description into structured JobRequirements.
  3. Explain a match score that Python already calculated.

It never invents the score itself - see matching/scorer.py for why.
"""

import json
import logging

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.config import get_settings
from app.models.schemas import ResumeData, JobRequirements, MatchResult
from app.services.errors import MissingAPIKeyError, LLMFailureError, InvalidExtractedDataError

logger = logging.getLogger(__name__)

RESUME_EXTRACTION_PROMPT = """You are an information extraction engine for a resume screening tool.

Read the resume text and return ONLY a JSON object with this exact shape:
{
  "name": string or null,
  "email": string or null,
  "phone": string or null,
  "skills": array of strings (technical and professional skills, deduplicated),
  "experience_years": number (best estimate of TOTAL years of professional experience, as a decimal),
  "education": array of strings (degree + institution, one entry per qualification)
}

Rules:
- Do not invent information that is not in the text.
- If a field cannot be determined, use null (or an empty array for lists).
- experience_years should be your best numeric estimate based on dates/roles mentioned.
- Return ONLY the JSON object, no markdown, no commentary.
"""

JOB_EXTRACTION_PROMPT = """You are an information extraction engine for a job description parser.

Read the job description and return ONLY a JSON object with this exact shape:
{
  "job_title": string or null,
  "required_skills": array of strings (must-have technical/professional skills),
  "preferred_skills": array of strings (nice-to-have skills, or "bonus"/"plus" skills),
  "minimum_experience": number (minimum years of experience required, 0 if not stated),
  "location": string or null
}

Rules:
- Separate "required" vs "preferred" skills based on the language used (e.g. "must have" vs "nice to have").
- If no distinction is made, treat all listed skills as required.
- Return ONLY the JSON object, no markdown, no commentary.
"""

EXPLANATION_PROMPT_TEMPLATE = """You are a recruiting assistant. A candidate has already been scored by a
deterministic Python scoring system against a job description. Your ONLY job is to explain the result in
2-4 concise, natural sentences for a recruiter. Do NOT change, question, or recalculate the score.

Job title: {job_title}

Score breakdown (already calculated, do not alter):
- Overall match score: {overall_score}/100
- Matched required skills: {matched_required}
- Missing required skills: {missing_required}
- Matched preferred skills: {matched_preferred}
- Candidate experience: {candidate_years} years (requirement: {required_years} years, meets requirement: {meets_requirement})
- Location match: {location_matches} (candidate: {candidate_location}, job: {job_location})

Write a short, professional explanation a recruiter could read in 5 seconds. Mention the strongest match
point and the most important gap, if any. Do not mention that you are an AI or that scoring was done in Python.
"""


def _get_client() -> OpenAI:
    settings = get_settings()
    if not settings.has_valid_api_key:
        raise MissingAPIKeyError(
            "No OpenAI API key configured. Set OPENAI_API_KEY in your .env file."
        )
    return OpenAI(api_key=settings.openai_api_key)


def _call_json(system_prompt: str, user_content: str) -> dict:
    """Call the chat completion endpoint and parse a JSON object response."""
    settings = get_settings()
    client = _get_client()

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except OpenAIError as exc:
        logger.exception("OpenAI API call failed")
        raise LLMFailureError(f"The LLM request failed: {exc}") from exc

    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise LLMFailureError(f"The LLM did not return valid JSON: {exc}") from exc


def extract_resume_data(resume_text: str) -> ResumeData:
    """Use the LLM to turn raw resume text into a structured ResumeData object."""
    raw = _call_json(RESUME_EXTRACTION_PROMPT, resume_text)
    try:
        data = ResumeData(**raw, raw_text_length=len(resume_text))
    except ValidationError as exc:
        raise InvalidExtractedDataError(f"Resume data failed validation: {exc}") from exc
    return data


def extract_job_requirements(job_description: str) -> JobRequirements:
    """Use the LLM to turn a job description into structured JobRequirements."""
    raw = _call_json(JOB_EXTRACTION_PROMPT, job_description)
    try:
        data = JobRequirements(**raw)
    except ValidationError as exc:
        raise InvalidExtractedDataError(f"Job requirement data failed validation: {exc}") from exc
    return data


def generate_explanation(match: MatchResult, job: JobRequirements) -> str:
    """Ask the LLM to explain a score Python already computed - not to invent one."""
    settings = get_settings()
    if not settings.has_valid_api_key:
        # Explanation is a "nice to have" on top of a working score - degrade
        # gracefully instead of failing the whole match request.
        return _fallback_explanation(match)

    prompt = EXPLANATION_PROMPT_TEMPLATE.format(
        job_title=job.job_title or "the role",
        overall_score=round(match.overall_score, 1),
        matched_required=", ".join(match.skills.matched_required) or "none",
        missing_required=", ".join(match.skills.missing_required) or "none",
        matched_preferred=", ".join(match.skills.matched_preferred) or "none",
        candidate_years=match.experience.candidate_years,
        required_years=match.experience.required_years,
        meets_requirement=match.experience.meets_requirement,
        location_matches=match.location.matches,
        candidate_location=match.location.candidate_location or "unknown",
        job_location=match.location.job_location or "not specified",
    )

    client = _get_client()
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = (response.choices[0].message.content or "").strip()
        return text or _fallback_explanation(match)
    except OpenAIError as exc:
        logger.warning("LLM explanation failed, falling back to template: %s", exc)
        return _fallback_explanation(match)


def _fallback_explanation(match: MatchResult) -> str:
    """A deterministic, template-based explanation used if the LLM call fails
    or no API key is configured, so the app still returns something useful."""
    parts = [f"Overall match score: {round(match.overall_score, 1)}/100."]
    if match.skills.matched_required:
        parts.append(f"Matches required skills: {', '.join(match.skills.matched_required)}.")
    if match.skills.missing_required:
        parts.append(f"Missing required skills: {', '.join(match.skills.missing_required)}.")
    if match.experience.meets_requirement:
        parts.append("Candidate meets the experience requirement.")
    else:
        parts.append("Candidate does not meet the stated experience requirement.")
    return " ".join(parts)
